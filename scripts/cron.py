#!/usr/bin/env python
# -*- coding: utf-8 -*-
# -------------------------------------------------------------
#  Community Calendar
#  Cron job to generate json files for event sources
# -------------------------------------------------------------

from icalendar import Calendar, Event
import urllib2
from dateutil import rrule
from datetime import datetime, timedelta, date
from pytz import timezone
import json
from eventbrite import Eventbrite
import os
from math import floor

import config
import logging

logging.basicConfig(format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.WARN)
logger = logging.getLogger(__name__)

dt_format = "%Y-%m-%dT%H:%M:%S"
tz = timezone(config.TZ)

# -------------------------------------------------------------
#  iCal parsing support functions
# -------------------------------------------------------------
def icalToString(ical_string):
	return ical_string.decode('string_escape').replace('\,', ',').replace('\;',';')

def icalToDict(event, output):
	output["title"] = event.get('summary').to_ical()

	try:
		output["description"] = icalToString(event.get('description').to_ical())
	except AttributeError:
		pass

	try:
		output["location"] = icalToString(event.get('location').to_ical())
	except AttributeError:
		pass

	try:
		output["url"] = icalToString(event.get('url').to_ical())
	except AttributeError:
		pass

# -------------------------------------------------------------
#  Parse iCal from URL
# -------------------------------------------------------------

def parseIcal(url):
	req = urllib2.Request(url, headers={ 'User-Agent': 'Mozilla/5.0' }) #required for Meetup :(
	try:
		response = urllib2.urlopen(req)
	except urllib2.URLError as err:
		logger.error("Error while fetching %s: %s" % (url, err.msg))
		raise

	data = response.read()

	try:
		cal = Calendar.from_ical(data)
	except ValueError:
		logger.error("Error parsing feed " + url)
		raise

	today = datetime.now(tz).replace(hour=0,minute=0)
	time_min = today + timedelta(days = -60)
	time_max = today + timedelta(days = 1*180)

	event_list = []

	for event in cal.walk('vevent'):
		if "rrule" in event:
			rule = rrule.rrulestr(event.get('rrule').to_ical(), dtstart=event.get('dtstart').dt)
			duration = event.get('dtend').dt - event.get('dtstart').dt

			for revent in rule.between(time_min, time_max):
				event_data = {
					"start": revent.strftime(dt_format),
					"end": (revent + duration).strftime(dt_format)
				}

				icalToDict(event, event_data)

				event_list.append((event, event_data))

		else:
			dtstart = event.get('dtstart').dt

			try:
				dtend = event.get('dtend').dt
			except AttributeError:
				dtend = dtstart

			if type(dtstart) is date:
				event_data = {
					"start": dtstart.strftime(dt_format),
					"end": dtend.strftime(dt_format),
					"allDay": True
				}

			else:
				if dtstart.tzinfo:
					dtstart = dtstart.astimezone(tz)
				if dtend.tzinfo:
					dtend = dtend.astimezone(tz)

				event_data = {
					"start": dtstart.strftime(dt_format),
					"end": dtend.strftime(dt_format)
				}

			icalToDict(event, event_data)

			event_list.append((event, event_data))

	# Function for reduce operation below
	def check_for_modified_reoccurences(old_items, new_item):
		# check all events for duplicate UIDs
		for n, item in enumerate(old_items):
			# ignore events not on the same day
			if datetime.strptime(item[1]["start"], dt_format).date() != datetime.strptime(new_item[1]["start"], dt_format).date():
				continue
			if item[0].get('uid') == new_item[0].get('uid'):
				# Duplicate UID found
				# The original item has no "RECURRENCE-ID" set, the updated one does
				if "RECURRENCE-ID" in new_item[0]:
					# new item the updated one
					# remove the old entry, fill in the new one
					del old_items[n]
					old_items.append(new_item)
				# if the old one is the updated one, just ignore the new item and move on
				return old_items

		# first item, or simply duplicate UIDs found
		old_items.append(new_item)
		return old_items

	# filter modified recurrences
	event_list = reduce(check_for_modified_reoccurences, event_list, [])
	# pass on only the second part of the tuples, the event_data
	event_list = map(lambda x: x[1], event_list)
	return event_list

# -------------------------------------------------------------
#  Get all events from a specific Eventbrite organizer
# -------------------------------------------------------------

def parseEventbrite(organizer):
	eventbrite = Eventbrite(config.EVENTBRITE_OAUTH_TOKEN)
	events = eventbrite.event_search(**{'organizer.id': organizer})

	event_list = []
	venues = {}

	for event in events["events"]:
		event_data = {
			"title": event["name"]["text"],
			"start": event["start"]["local"],
			"end": event["end"]["local"],
			"url": event["url"]
		}

		try:
			event_data["description"] = event["description"]["text"]
		except AttributeError:
			pass

		venue_id = event["venue_id"]
		try:
			venue_str = venues[venue_id]
		except KeyError:
			venue = eventbrite.get("/venues/%s" % venue_id)
			venue_str = "%s, %s, %s %s" % (venue["name"], venue["address"]["address_1"], venue["address"]["postal_code"], venue["address"]["city"])
			venues[venue_id] = venue_str

		event_data["location"] = venue_str

		event_list.append(event_data)

	return event_list

def parseFacebookPage(pageid):
	url = "https://graph.facebook.com/v2.10/%s/events?time_filter=upcoming&access_token=%s" % (pageid, config.FACEBOOK_TOKEN)
	req = urllib2.Request(url)
	try:
		response = urllib2.urlopen(req)
	except urllib2.URLError as err:
		logger.error("Error while fetching %s: %s" % (url, err.msg))
		raise

	data_raw = response.read()
	data = json.loads(data_raw)

	event_list = []

	for fb_event in data["data"]:
		start_time, _ = fb_event["start_time"].split('+')
		end_time, _ = fb_event["end_time"].split('+')
		try:
			location = "%s (%s, %s %s)" % (
				fb_event["place"]["name"],
				fb_event["place"]["location"]["street"],
				fb_event["place"]["location"]["zip"],
				fb_event["place"]["location"]["city"])
		except:
			location = ""

		event_data = {
			"title": fb_event["name"],
			"description": fb_event["description"],
			"start": start_time,
			"end": end_time,
			"location": location,
			"url": fb_event["id"]
		}

		event_list.append(event_data)

	return event_list

# -------------------------------------------------------------
#  parse an event source
# -------------------------------------------------------------

def getEvents(source):
	if source["type"] == "eventbrite":
		return parseEventbrite(source["organizer"])
	elif source["type"] == "ics":
		return parseIcal(source["url"])
	elif source["type"] == "facebook":
		return parseFacebookPage(source["page_id"])
	elif source["type"] == "multiple":
		events = []
		for source in source["sources"]:
			events += getEvents(source)
		return events

# -------------------------------------------------------------
#  Parse Event Sources and generate JSON files
# -------------------------------------------------------------

frontend_sources = []
all_events = []

directory = os.path.dirname(os.path.realpath(__file__))

for source in config.SOURCES:
	filename = "data/" + source["name"] + ".json"
	from_cache = False
	try:
		events = getEvents(source)
	except Exception as e:
		logger.warn("Could not read source '%s': %s" % (source["title"], e))

		try:
			t = os.path.getmtime(filename)
		except:
			continue

		mdate = datetime.fromtimestamp(t)
		delta = datetime.now() - mdate
		delta_hours = floor(delta.total_seconds() / 3600)
		if delta_hours > 0 and delta_hours % 12 == 0:
			logger.warn("Source '%s' has been unavailable for %d hours"
					% (source["title"], delta_hours))
		from_cache = True
		with open(directory + "/" + filename) as data_file:
			events = json.load(data_file)

	all_events += events

	if not from_cache:
		f = open(directory + "/" + filename, "w")
		f.write(json.dumps(events))
		f.close

	frontend_sources.append({
		"url": filename,
		"title": source["title"],
		"color": source["color"]
	})

filename = directory + "/data/_sources.json"
f = open(filename, "w")
f.write(json.dumps(frontend_sources))
f.close

# -------------------------------------------------------------
#  Generate iCal
# -------------------------------------------------------------

cal = Calendar()
cal.add('prodid', '-//community_calendar//tiefpunkt//')
cal.add('version', '2.0')
cal.add('X-WR-CALNAME', config.ICAL_CALNAME)

for event in all_events:
	vevent = Event()
	vevent.add("summary", event["title"])

	try:
		vevent.add("description", event["description"])
	except KeyError:
		pass

	try:
		vevent.add("url", event["url"])
	except KeyError:
		pass

	try:
		vevent.add("location", event["location"])
	except KeyError:
		pass

	vevent.add("dtstart", datetime.strptime(event['start'], dt_format).replace(tzinfo=tz))
	vevent.add("dtend", datetime.strptime(event['end'], dt_format).replace(tzinfo=tz))

	cal.add_component(vevent)

filename = directory + "/data/all.ics"
f = open(filename, "w")
f.write(cal.to_ical())
f.close()

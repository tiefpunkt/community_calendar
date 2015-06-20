#!/usr/bin/python
# -*- coding: utf-8 -*-

from icalendar import Calendar
import urllib2
from dateutil import rrule
from datetime import datetime, timedelta, date
from pytz import timezone
import json
from eventbrite import Eventbrite
import config

dt_format = "%Y-%m-%dT%H:%M:%S"
tz = timezone(config.TZ)

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

def parseIcal(url):
	req = urllib2.Request(url, headers={ 'User-Agent': 'Mozilla/5.0' }) #required for Meetup :(
	response = urllib2.urlopen(req)
	data = response.read()
	cal = Calendar.from_ical(data)

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

				event_list.append(event_data)

		else:
			dtstart = event.get('dtstart').dt
			dtend = event.get('dtend').dt

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

			event_list.append(event_data)


	return event_list

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
			venue = eventbrite.get("/venues/" + venue_id)
			venue_str = venue["name"] + ", "
			venue_str += venue["address"]["address_1"] +", "
			venue_str += venue["address"]["postal_code"] + " " + venue["address"]["city"]
			venues[venue_id] = venue_str

		event_data["location"] = venue_str

		event_list.append(event_data)

	return event_list

def getEvents(source):
	if source["type"] == "eventbrite":
		return parseEventbrite(source["organizer"])
	elif source["type"] == "ics":
		return parseIcal(source["url"])
	elif source["type"] == "multiple":
		events = []
		for source in source["sources"]:
			events += getEvents(source)
		return events

frontend_sources = []

for source in config.SOURCES:
	events = getEvents(source)

	filename = "data/" + source["name"] + ".json"
	f = open(filename, "w")
	f.write(json.dumps(events))
	f.close

	frontend_sources.append({
		"url": filename,
		"title": source["title"],
		"color": source["color"]
	})

filename = "data/_sources.json"
f = open(filename, "w")
f.write(json.dumps(frontend_sources))
f.close

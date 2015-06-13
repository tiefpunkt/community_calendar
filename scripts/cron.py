from icalendar import Calendar
import urllib2
from dateutil import rrule
from datetime import datetime, timedelta, date
from pytz import timezone
import json
from eventbrite import Eventbrite
import config

tz = timezone("Europe/Berlin")
dt_format = "%Y-%m-%dT%H:%M:%S"

sources = [
		{
			"name": "muccc",
			"type": "ics",
			"url": "http://api.muc.ccc.de/wiki_kalender.ics"
		},
		{
			"name": "werkbox",
			"type": "ics",
			"url": "http://www.werkbox3.de/events.ics"
		},
		{
			"name": "arduino_meetup",
			"type": "ics",
			"url": "http://www.meetup.com/Munchen-Arduino-Meetup/events/ical/"
		},
		{
			"name":"mumalab",
			"type": "ics",
			"url": "https://www.google.com/calendar/ical/lbd0aa2rlahecp7juvp35hd0k0%40group.calendar.google.com/public/basic.ics"
		},
		{
			"name": "fablab",
			"type": "multiple",
			"sources": [
				{
					"type": "eventbrite",
					"organizer": "7227151391"
				},
				{
					"type": "eventbrite",
					"organizer": "7117094347"
				}
			]
		}
	]

def parseIcal(url):
	req = urllib2.Request(url, headers={ 'User-Agent': 'Mozilla/5.0' })
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
					"title": event.get('summary').to_ical(),
					"start": revent.strftime(dt_format),
					"end": (revent + duration).strftime(dt_format)
				}

				try:
					event_data["description"] = event.get('description').to_ical()
				except AttributeError:
					pass

				event_list.append(event_data)

		else:
			event_data = {
				"title": event.get('summary').to_ical(),
				"start": event.get('dtstart').dt.strftime(dt_format),
				"end": event.get('dtend').dt.strftime(dt_format)
			}

			try:
				event_data["description"] = event.get('description').to_ical()
			except AttributeError:
				pass

			event_list.append(event_data)


	return event_list

def parseEventbrite(organizer):
	eventbrite = Eventbrite(config.EVENTBRITE_OAUTH_TOKEN)
	events = eventbrite.event_search(**{'organizer.id': organizer})

	event_list = []

	for event in events["events"]:
		event_data = {
			"title": event["name"]["text"],
			"start": event["start"]["local"],
			"end": event["end"]["local"]
		}

		try:
			event_data["description"] = event["description"]["text"]
		except AttributeError:
			pass

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

for source in sources:
	events = getEvents(source)

	filename = "data/" + source["name"] + ".json"
	f = open(filename, "w")
	f.write(json.dumps(events))
	f.close

#!/usr/bin/env python
# -*- coding: utf-8 -*-
# -------------------------------------------------------------
#  Community Calendar
#  Cron job to generate json files for event sources
# -------------------------------------------------------------

from icalendar import Calendar, Event
import urllib.request, urllib.error, urllib.parse
from dateutil import rrule
from datetime import datetime, timedelta, date
from pytz import timezone
import json
from eventbrite import Eventbrite
import os
from math import floor
from dateutil.parser import parse
import sys

# Microdata
import microdata
from urllib.parse import urljoin

# FB Fallback
import re
from bs4 import BeautifulSoup
import requests
import dateparser

import config
import logging
from functools import reduce

import traceback

logging.basicConfig(format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.WARN)
logger = logging.getLogger(__name__)

dt_format = "%Y-%m-%dT%H:%M:%S"
tz = timezone(config.TZ)

# -------------------------------------------------------------
#  iCal parsing support functions
# -------------------------------------------------------------
def icalToString(ical_string):
    return ical_string.decode('unicode_escape').replace(r"\\,", ',').replace(r"\\;",';')

def icalToDict(event, output):
    output["title"] = event.get('summary').to_ical().decode("utf-8")

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
    req = urllib.request.Request(url, headers={ 'User-Agent': 'Mozilla/5.0' }) #required for Meetup :(
    try:
        response = urllib.request.urlopen(req)
    except urllib.error.URLError as err:
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
            rule = rrule.rruleset()
            rule.rrule(rrule.rrulestr(event.get('rrule').to_ical().decode("utf-8"), dtstart=event.get('dtstart').dt))
                        
            if "exdate" in event:
                exdates = event.get("exdate")
                if not isinstance(exdates, list):
                    exdates = [exdates]
                for exdate in exdates:
                    rule.exdate(exdate.dts[0].dt)

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
    event_list = [x[1] for x in event_list]
    return event_list

# -------------------------------------------------------------
#  Get all events from a specific Eventbrite organizer
# -------------------------------------------------------------

def parseEventbrite(organizer):
    eventbrite = Eventbrite(config.EVENTBRITE_OAUTH_TOKEN)
    events = eventbrite.get_organizer_events(organizer)

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
    req = urllib.request.Request(url)
    try:
        response = urllib.request.urlopen(req)
    except urllib.error.URLError as err:
        logger.error("Error while fetching %s: %s" % (url, err.msg))
        raise

    data_raw = response.read()
    data = json.loads(data_raw)

    event_list = []

    for fb_event in data["data"]:
        start_time, _ = fb_event["start_time"].split('+')
        try:
            end_time, _ = fb_event["end_time"].split('+')
        except:
            # Some events dont have an endtime
            end_time_tmp = parse(start_time) + timedelta(hours = 1)
            end_time = end_time_tmp.strftime(dt_format)

        try:
            location = "%s (%s, %s %s)" % (
                fb_event["place"]["name"],
                fb_event["place"]["location"]["street"],
                fb_event["place"]["location"]["zip"],
                fb_event["place"]["location"]["city"])
        except:
            try:
                location = fb_event["place"]["name"]
            except:
                location = ""

        event_data = {
            "title": fb_event["name"],
            "description": fb_event["description"],
            "start": start_time,
            "end": end_time,
            "location": location,
            "url": "https://www.facebook.com/events/%s" % fb_event["id"]
        }

        if "event_times" in fb_event:
            for event_time in fb_event["event_times"]:
                event_data_rec = event_data.copy()
                event_data_rec["url"] = "https://www.facebook.com/events/%s" % event_time["id"]
                event_data_rec["start"], _ = event_time["start_time"].split('+')
                try:
                    event_data_rec["end"], _ = event_time["end_time"].split('+')
                except:
                    end_time_tmp = parse(event_data_rec["start"]) + timedelta(hours = 1)
                    event_data_rec["end"] = end_time_tmp.strftime(dt_format)
                event_list.append(event_data_rec)
        else:
            event_list.append(event_data)

    if len(event_list) == 0:
        event_list=parseFacebookPageFallback(pageid)

    return event_list

def parseFacebookPageFallback(pageid):

    def _parseEventPages(event_urls):
        event_list = []
        for url in event_urls:
            try:
                res = ses.get(url)
                c = BeautifulSoup(res.content,"html.parser")
                title = c.title.text
                subevents = c.find_all("a",{"href":re.compile("event_time_id=\d*")})

                if subevents:
                    logger.warning("[%s] %s has subevents" % (pageid,title))
                    subevent_urls = ["https://mbasic.facebook.com%s" % subevent["href"] for subevent in subevents]

                    subevent_list = _parseEventPages(subevent_urls)
                    event_list += subevent_list
                    continue

                times = c.find("div",string=re.compile(".*UTC\+\d\d")).string
                #m = re.match("(\w*), (\d*)\. (\w*) (\S*) - (\S*) (UTC\+\d\d)", times)
                m = re.match("(\w*), (\d*)\. (\w* \d*) von (\S*) bis (\S*) (UTC\+\d\d)", times)
                if m:
                    start = dateparser.parse("%s, %s. %s %s %s00" % (m.group(1), m.group(2), m.group(3), m.group(4), m.group(6)))
                    end = dateparser.parse("%s, %s. %s %s %s00" % (m.group(1), m.group(2), m.group(3), m.group(5), m.group(6)))
                else:
                    m = re.match("(\w*), (\d* \w*)\. (\w*) um (\S*) (UTC\+\d\d)", times)
                    if m:
                        start = dateparser.parse("%s, %s. %s %s %s00" % (m.group(1), m.group(2), m.group(3), m.group(4), m.group(5)))
                        end = start + timedelta(hours = 1)
                    else:
                        # e.g. "Freitag, 20. September 2019 um 12:00 UTC+02"
                        m = re.match("(\w*), (\d*)\. (\w*) (\w*) um (\S*) (UTC\+\d\d)", times)
                        if m:
                            start = dateparser.parse("%s, %s. %s %s %s %s00" % (m.group(1), m.group(2), m.group(3), m.group(4), m.group(5), m.group(6)))
                            end = start + timedelta(hours = 1)
                        else:
                            m = re.match("(\d*)\. (\w*) um (\S*) . (\d*)\. (\w*) um (\S*) (UTC\+\d\d)", times)
                            if m:
                                start = dateparser.parse("%s. %s %s %s00" % (m.group(1), m.group(2), m.group(3), m.group(7)))
                                end = dateparser.parse("%s. %s %s %s00" % (m.group(4), m.group(5), m.group(6), m.group(7)))
                            else:
                                logger.error("[%s] %s does not match time filter" % (pageid,title))
                                continue
                id = re.search("/events/(\d*)",url).group(1)
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                logger.error("[%s] %s (%s,%s,%s)" % (pageid,e,fname,exc_tb.tb_lineno,url))
                continue
            event_data = {
                "title": title,
                #"description": "",
                "start": start.strftime(dt_format),
                "end": end.strftime(dt_format),
                #"location": location,
                #"url": url
                "url": "https://www.facebook.com/events/%s" % id
            }
            #print ("* %s (%s)" % (event_data["title"], id))

            event_list.append(event_data)

        return event_list

    url="https://mbasic.facebook.com/%s/events/" % pageid
    user_agent = {'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/66.0.3359.181 Safari/537.36', "accept-language": "de-DE,de"}
    ses = requests.Session()
    ses.headers = user_agent
    res = ses.get(url)
    c = BeautifulSoup(res.content,"html.parser")
    events = c.find_all("a", {"href":re.compile("/events/.*")})
    event_urls = ["https://mbasic.facebook.com%s" % event["href"] for event in events]

    event_list = _parseEventPages(event_urls)

    filename = "debug.%s.html" % pageid
    f = open(filename, "w")
    f.buffer.write(res.content)
    f.close()
    return event_list

def parseMicrodata(url):
    req = urllib.request.Request(url)
    try:
        response = urllib.request.urlopen(req)
    except urllib.error.URLError as err:
        logger.error("Error while fetching %s: %s" % (url, err.msg))
        raise

    items = microdata.get_items(response)

    event_list = []

    for ev in [x for x in items if microdata.URI("http://schema.org/Event") in x.itemtype]:
        start = datetime.strptime(ev.startdate, "%Y-%m-%dT%H:%M:%SZ")
        start = start.replace(tzinfo=timezone("UTC")).astimezone(tz)

        if (ev.enddate):
            end = datetime.strptime(ev.startdate, "%Y-%m-%dT%H:%M:%SZ")
            end = end.replace(tzinfo=timezone("UTC"))
        else:
            end = start + timedelta(hours = 1)

        event_data = {
            "title": ev.name,
            "description": ev.name,
            "start": start.strftime(dt_format),
            "end": end.strftime(dt_format),
            "location": ev.location.name,
            "url": urljoin (url, str(ev.url))
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
        return parseFacebookPageFallback(source["page_id"])
    elif source["type"] == "microdata":
        return parseMicrodata(source["url"])
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
        logger.warning("Could not read source '%s': %s" % (source["title"], e))
        traceback.print_exc()
        events = []

    if len(events) == 0:
        logger.warning("No events from API for '%s'" % (source["title"]))
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
f.buffer.write(cal.to_ical())
f.close()

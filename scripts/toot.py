#!/usr/bin/env python
# -*- coding: utf-8 -*-
# encoding=utf8

import json
import os
import sys
from datetime import datetime, timedelta, date
from pytz import timezone
from mastodon import Mastodon
import logging

import config

def toot(status):
	logger.info("sending toot (%s): %s" % (len(status), status))

	try:
		mastodon.status_post(status)
	except:
		logger.error("error sending toot (%s): %s" % (len(status), status))

logging.basicConfig(filename='toott.log', format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

if config.MASTODON_ENABLED != True:
	logger.info("Mastodon propagation not enabled.")
	sys.exit(0)

directory = os.path.dirname(os.path.realpath(__file__))
all_events = []
dt_format_json = "%Y-%m-%dT%H:%M:%S"
dt_format_twitter = "%d.%m.%Y %H:%M"
filename = directory + "/data/_sources.json"

tz = timezone(config.TZ)
today = datetime.now(tz).replace(hour=0,minute=0)
time_min = today + timedelta(days=config.DAYS_AHEAD)
time_max = today + timedelta(days=config.DAYS_AHEAD + 1)

# Toot API
mastodon = Mastodon(
    access_token = config.MASTODON_ACCESS_TOKEN,
    api_base_url = config.MASTODON_URL
)

with open(filename) as data_file:
	sources = json.load(data_file)

for source in config.SOURCES:
	events = []
	try:
		with open("%s/data/%s.json" % (directory, source['name'])) as data_file:
			events = json.load(data_file)
			all_events += events
			logger.debug("loading %s" % source['title'])
	except:
		continue

	for event in events:
		dt_start = datetime.strptime(event['start'], dt_format_json).replace(tzinfo = tz)

		if dt_start >= time_min and dt_start < time_max:
			start_out = dt_start.strftime(dt_format_twitter)

			max_length = 140 - 23 - 6 - 16 - len(source['title'])
			if len(event['title']) > max_length:
				title = u"%s..." % event['title'][:max_length-3]
			else:
				title = u"%s" % event['title']

			if "url" in event:
				text = u"%s: %s @ %s %s" % (start_out, title, source['title'], event['url'])
			elif "website" in source:
				text = u"%s: %s @ %s %s" % (start_out, title, source['title'], source['website'])
			else:
				text = u"%s: %s @ %s" % (start_out, title, source['title'])
			toot(text)

logger.debug("loaded %s events" % len(all_events))

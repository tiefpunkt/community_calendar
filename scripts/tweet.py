#!/usr/bin/env python
# -*- coding: utf-8 -*-
# encoding=utf8

import json
import os
import sys
from datetime import datetime, timedelta, date
from pytz import timezone
import tweepy
import logging
import yaml
from argparse import Namespace

def loadConfig():
    with open(os.path.dirname(os.path.realpath(__file__)) + '/config.yaml', 'r') as ymlfile:
        cfg = yaml.safe_load(ymlfile)
    
    ns = Namespace(**cfg)
    return ns

config = loadConfig()

def tweet(status):
	logger.info("sending tweet (%s): %s" % (len(status), status))

	try:
		api.update_status(status)
	except:
		logger.error("error sending tweet (%s): %s" % (len(status), status))

logging.basicConfig(filename='tweet.log', format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

if config.TWITTER_ENABLED != True:
	logger.info("Twitter propagation not enabled.")
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

# Twitter API
auth = tweepy.OAuthHandler(config.TWITTER_CONSUMER_KEY, config.TWITTER_CONSUMER_SECRET)
auth.set_access_token(config.TWITTER_ACCESS_KEY, config.TWITTER_ACCESS_SECRET)
api = tweepy.API(auth)

with open(filename) as data_file:
	sources = json.load(data_file)

for source_name, source_config in config.SOURCES.items():
	events = []
	try:
		with open("%s/data/%s.json" % (directory, source_name)) as data_file:
			events = json.load(data_file)
			all_events += events
			logger.debug("loading %s" % source_config['title'])
	except:
		continue

	for event in events:
		dt_start = datetime.strptime(event['start'], dt_format_json).replace(tzinfo = tz)

		if dt_start >= time_min and dt_start < time_max:
			start_out = dt_start.strftime(dt_format_twitter)

			max_length = 140 - 23 - 6 - 16 - len(source_config['title'])
			if len(event['title']) > max_length:
				title = u"%s..." % event['title'][:max_length-3]
			else:
				title = u"%s" % event['title']

			if event.get("url"):
				text = u"%s: %s @ %s %s" % (start_out, title, source_config['title'], event['url'])
			elif source_config.get("website"):
				text = u"%s: %s @ %s %s" % (start_out, title, source_config['title'], source_config['website'])
			else:
				text = u"%s: %s @ %s" % (start_out, title, source_config['title'])
			tweet(text)

logger.debug("loaded %s events" % len(all_events))

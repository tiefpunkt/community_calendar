#!/bin/sh

# Setup crontab
env | grep PATH > /tmp/crontab
echo "20 * * * * 	python /app/scripts/cron.py" >> /tmp/crontab
echo "23 11 * * * 	python /app/scripts/tweet.py" >> /tmp/crontab
echo "23 11 * * *       python /app/scripts/toot.py" >> /tmp/crontab
crontab /tmp/crontab
rm /tmp/crontab

if [ ! -d "/data" ]; then
	mkdir /data
fi

if [ ! -f "/data/config.py" ]; then
	echo "Copying initial config ..."
	cp /app/scripts/config.py.sample /data/config.py
fi

if [ ! -d "/data/htdocs" ]; then
	echo "Copying html ..."
	cp -r /app/htdocs /data/
fi

echo "Initial data load..."
python /app/scripts/cron.py

# Start cron
echo "Starting cron ..."
cron

# Start webserver
echo "Starting webserver ..."
exec nginx -g "daemon off;"

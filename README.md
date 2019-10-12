# Community Calendar

A shared calendar for communities of different organisations. Merges calendars from different sources into one, with two web interfaces (a "normal" calendar, and agenda that also works great on digital signage), a merged ICS file, and a ttwitter bot (if wanted).

## Supported sources
* ICS/iCal calendar feed (like Google Calendar)
* Eventbrite organisation
* Facebook page
* Microdata

## Requirements
* Python
* virtualenv
* A webserver of sorts

## Setup
```
git clone https://github.com/tiefpunkt/community_calendar.git <directory>
cd <directory>
cd scripts
virtualenv env
. env/bin/activate
pip install --upgrade -r requirements.txt
deactivate
cp config.py.sample config.py
vi config.py
crontab -e
```

Now point webserver to the htdocs directory

Alternatively, build the whole thing as a docker image, using the provided Dockerfile.

## Active Deployments
* [Munich Makes](https://calendar.munichmakes.de/) ([@munichmakes](https://twitter.com/munichmakes))
* [Kreativquartier München](https://kreativquartier.munichmakes.de/agenda/)
* [Events For Future München](https://forfuture.munichmakes.de/agenda) ([@fff_events_muc](https://twitter.com/fff_events_muc))

# License
Licensed under MIT License. See [LICENSE](./LICENSE) for details.

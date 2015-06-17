# Community Calendar

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

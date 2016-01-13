FROM python:2.7

RUN apt-get -y update && apt-get install -y nginx
#RUN git clone https://github.com/tiefpunkt/community_calendar.git /app
COPY . /app
RUN pip install --upgrade -r /app/scripts/requirements.txt
#COPY scripts/config.py /app/scripts/

# forward request and error logs to docker log collector
RUN ln -sf /dev/stdout /var/log/nginx/access.log
RUN ln -sf /dev/stderr /var/log/nginx/error.log

RUN rm -rf /var/www/html && ln -sf /app/htdocs /var/www/html
RUN python /app/scripts/cron.py
RUN ln -sf /app/scripts/cron.py /etc/cron.daily/community_calendar

EXPOSE 80 443

CMD ["nginx", "-g", "daemon off;"]

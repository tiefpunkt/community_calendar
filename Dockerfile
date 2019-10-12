FROM python:2.7

RUN apt-get update && \
  apt-get install -y nginx cron --no-install-recommends

COPY scripts/requirements.txt /app/scripts/requirements.txt

RUN pip install --upgrade -r /app/scripts/requirements.txt

COPY . /app

# forward request and error logs to docker log collector
RUN ln -sf /dev/stdout /var/log/nginx/access.log
RUN ln -sf /dev/stderr /var/log/nginx/error.log

RUN rm /app/htdocs/data; rm /app/scripts/config.py; ln -s /data/config.py /app/scripts/config.py

COPY nginx_site.conf /etc/nginx/sites-enabled/default

EXPOSE 80

CMD /app/entrypoint.sh

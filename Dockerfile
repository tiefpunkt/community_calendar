FROM python:2.7

RUN apt-get update && \
  apt-get install -y nginx cron --no-install-recommends

COPY . /app

RUN pip install --upgrade -r /app/scripts/requirements.txt

# forward request and error logs to docker log collector
RUN ln -sf /dev/stdout /var/log/nginx/access.log
RUN ln -sf /dev/stderr /var/log/nginx/error.log

RUN rm /app/htdocs/data

COPY nginx_site.conf /etc/nginx/sites-enabled/default

CMD /app/entrypoint.sh

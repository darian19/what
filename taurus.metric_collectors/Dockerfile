FROM htmengine:latest
ADD . /opt/numenta/taurus.metric_collectors
WORKDIR /opt/numenta/taurus.metric_collectors
RUN python setup.py develop --install-dir=/usr/local/lib/python2.7/site-packages --script-dir=/usr/local/bin
ENV APPLICATION_CONFIG_PATH=/opt/numenta/taurus.metric_collectors/conf \
    RABBITMQ_HOST=rabbit \
    RABBITMQ_USER=guest \
    RABBITMQ_PASSWD=guest \
    MYSQL_HOST=mysql \
    MYSQL_USER=root \
    MYSQL_PASSWD=taurus \
    TAURUS_HTM_SERVER=taurus \
    TAURUS_METRIC_COLLECTORS_LOG_DIR=/opt/numenta/taurus.metric_collectors/logs \
    TAURUS_TWITTER_ACCESS_TOKEN=OVERRIDE_ME \
    TAURUS_TWITTER_ACCESS_TOKEN_SECRET=OVERRIDE_ME \
    TAURUS_TWITTER_CONSUMER_KEY=OVERRIDE_ME \
    TAURUS_TWITTER_CONSUMER_SECRET=OVERRIDE_ME \
    XIGNITE_API_TOKEN=OVERRIDE_ME
RUN mkdir -p /opt/numenta/taurus.metric_collectors/logs
EXPOSE 8001
CMD ./docker/taurus.metric_collectors/run-taurus.metric_collectors.sh

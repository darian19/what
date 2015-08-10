FROM taurus.metric_collectors:latest
RUN apt-get install -y nginx
ADD . /opt/numenta/taurus
WORKDIR /opt/numenta/taurus
RUN python setup.py develop --install-dir=/usr/local/lib/python2.7/site-packages --script-dir=/usr/local/bin
ENV APPLICATION_CONFIG_PATH=/opt/numenta/taurus/conf \
    RABBITMQ_HOST=rabbit \
    RABBITMQ_USER=guest \
    RABBITMQ_PASSWD=guest \
    MYSQL_HOST=mysql \
    MYSQL_USER=root \
    MYSQL_PASSWD=taurus \
    DYNAMODB_HOST=dynamodb \
    DYNAMODB_PORT=8300 \
    TAURUS_RMQ_METRIC_DEST=rabbit \
    TAURUS_RMQ_METRIC_PREFIX=docker
RUN mkdir -p /opt/numenta/taurus/logs
EXPOSE 443 9001
CMD ./docker/taurus/run-taurus.sh

#!/bin/bash

set -o errexit

sysctl -w net.core.somaxconn=1024
cp /opt/numenta/taurus/docker/htmengine/conf/supervisord-base.conf /opt/numenta/htmengine/conf/
cp /opt/numenta/taurus/docker/taurus/conf/application.conf /opt/numenta/taurus/conf/
cp /opt/numenta/taurus/docker/taurus/conf/nginx-taurus.conf /opt/numenta/taurus/conf/
cp /opt/numenta/taurus/docker/taurus/conf/supervisord.conf /opt/numenta/taurus/conf/
mkdir -p /opt/numenta/taurus/conf/ssl/
cp /opt/numenta/taurus/docker/taurus/conf/ssl/* /opt/numenta/taurus/conf/ssl/
taurus-set-rabbitmq --host=${RABBITMQ_HOST} --user=${RABBITMQ_USER} --password=${RABBITMQ_PASSWD}
taurus-set-sql-login --host=${MYSQL_HOST} --user=${MYSQL_USER} --password=${MYSQL_PASSWD}
taurus-set-dynamodb --host=${DYNAMODB_HOST} --port=${DYNAMODB_PORT} --table-suffix=.local --security-off
taurus-create-db --suppress-prompt-and-continue-with-deletion
nginx -p . -c /opt/numenta/taurus/conf/nginx-taurus.conf
supervisord -c /opt/numenta/taurus/conf/supervisord.conf --nodaemon

#!/bin/bash

set -o errexit

taurus-set-collectorsdb-login --host=${MYSQL_HOST} --user=${MYSQL_USER} --password=${MYSQL_PASSWD}
taurus-collectors-set-rabbitmq --host=${RABBITMQ_HOST} --user=${RABBITMQ_USER} --password=${RABBITMQ_PASSWD}
taurus-reset-collectorsdb --suppress-prompt-and-obliterate-database
supervisord -c /opt/numenta/taurus.metric_collectors/conf/supervisord.conf --nodaemon

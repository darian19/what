# ----------------------------------------------------------------------
# Numenta Platform for Intelligent Computing (NuPIC)
# Copyright (C) 2015, Numenta, Inc.  Unless you have purchased from
# Numenta, Inc. a separate commercial license for this software code, the
# following terms and conditions apply:
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 3 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see http://www.gnu.org/licenses.
#
# http://numenta.org/licenses/
# ----------------------------------------------------------------------

FROM phusion/baseimage:latest 
RUN apt-get update
RUN DEBIAN_FRONTEND=noninteractive apt-get install -y openjdk-7-jre wget
WORKDIR /opt
RUN wget --no-check-certificate -O- https://download.elasticsearch.org/elasticsearch/elasticsearch/elasticsearch-1.4.4.tar.gz | tar xvfz -
RUN mv elasticsearch-1.4.4 elasticsearch

RUN cd elasticsearch && bin/plugin -install elasticsearch/elasticsearch-cloud-aws/2.4.1
RUN cd elasticsearch && bin/plugin -install mobz/elasticsearch-head
RUN cd elasticsearch && bin/plugin -install lmenezes/elasticsearch-kopf/1.4.4
RUN cd elasticsearch && bin/plugin -install lukas-vlcek/bigdesk

ENV ES_CLUSTER_NAME elasticsearch
ENV ES_AWS_REGION us-east-1

EXPOSE 9200 9300

ADD es_rotate /opt/es_rotate
RUN chmod +x /opt/es_rotate

ADD es.crontab /opt/es.crontab
RUN crontab /opt/es.crontab

VOLUME ["/opt/elasticsearch/data", "/opt/elasticsearch/config"]

RUN mkdir -p /etc/service/elasticsearch
ADD run.sh /etc/service/elasticsearch/run
RUN chmod +x /etc/service/elasticsearch/run

# Use baseimage-docker's init system.
CMD ["/sbin/my_init"]

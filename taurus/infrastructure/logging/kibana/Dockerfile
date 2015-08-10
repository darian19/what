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
RUN apt-get install -y nginx
RUN mkdir /etc/service/kibana
ADD run.sh /etc/service/kibana/run
RUN chmod +x /etc/service/kibana/run 

# Use baseimage-docker's init system.
CMD ["/sbin/my_init"]

ADD https://download.elasticsearch.org/kibana/kibana/kibana-3.1.0.tar.gz /tmp/kibana.tar.gz
RUN tar zxf /tmp/kibana.tar.gz && mv kibana-3.1.0/* /usr/share/nginx/html
EXPOSE 80


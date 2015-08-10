Taurus logging services
=======================

Create SSL certificates:

```
mkdir -p logstash/ssl
cd logstash/ssl
openssl req -x509  -batch -nodes -newkey rsa:2048 -keyout taurus-lumberjack.key -out taurus-lumberjack.crt -subj /CN=<TARGET HOSTNAME>
```

Remember to copy those files to /opt/numenta/products/taurus/conf/ssl!

Build and run docker containers:

```
sudo docker build -t elasticsearch elasticsearch/
sudo docker run -v /mnt/elasticsearch-0:/opt/elasticsearch/data -v `pwd`/elasticsearch/config:/opt/elasticsearch/config -p 9200:9200 -p 9300:9300 -d elasticsearch
```

Wait for elasticsearch container to become available, and issue this command to define the logstash index template:

```
curl -XPUT 'http://localhost:9200/_template/template_logstash/' -d @elasticsearch/logstash-template.json
```

Then:

```
sudo docker build -t logstash logstash/
sudo docker run -p 514:514 -p 514:514/udp -p 9292:9292 -p 12345:12345 -p 12345:12345/udp -v `pwd`/logstash/ssl:/opt/logstash/ssl -v `pwd`/logstash/conf:/opt/logstash/conf -v `pwd`/logstash/data:/etc/service/logstash/data -d logstash
sudo docker run -d -e ES_HOST=elasticsearch.numenta.com -e ES_PORT=9200 -p 0.0.0.0:80:80 kibana
```

logstash-forwarder
------------------

Use logstash-forwarder to ship logs to logstash via lumberjack protocol.  There's a Dockerfile in logstash-forwarder to facilitate building the logstash-forwarder binary.  See logstash-forwarder/README.md for details.



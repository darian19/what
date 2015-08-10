sudo docker build -t logstash-forwarder .
sudo docker run -v `pwd`:/mnt/host -ti logstash-forwarder cp bin/logstash-forwarder /mnt/host/

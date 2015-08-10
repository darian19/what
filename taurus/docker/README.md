Install dependencies
--------------------

* [VirtualBox](https://www.virtualbox.org/wiki/Downloads) 4.3.10 or greater.
* [Vagrant](http://www.vagrantup.com/downloads.html) 1.6 or greater.
* Docker Client that supports the `-f` arg (https://docs.docker.com/installation/mac/)

Startup
-------

From within the `infrastructure/coreos/` directory relative to `numenta-apps`
root:

```
vagrant up
source env
```

``vagrant up`` triggers vagrant to download the CoreOS image (if necessary)
and (re)launch the instance

Build and run Taurus Docker Image
---------------------------------

Taurus requires MySQL and RabbitMQ, so we'll run those daemons as separate
containers, and the full suite of taurus-specific supervisor services in
another.  We'll also be basing our taurus image on the official numenta/nupic
docker image to avoid building nupic.

In the root of `numenta-apps/`:

```
docker build -t nta.utils:latest nta.utils
docker build -t htmengine:latest htmengine
docker build -t taurus.metric_collectors:latest taurus.metric_collectors
docker build -t taurus:latest taurus
docker build -t taurus-dynamodb:latest taurus/external/dynamodb_test_tool
```

Start MySQL container(s):

```
docker run \
  --name taurus-mysql \
  -e MYSQL_ROOT_PASSWORD=taurus \
  -p 3306:3306 \
  -d \
  mysql:5.6
```

Start RabbitMQ container:

```
docker run \
  --name taurus-rabbit \
  -e RABBITMQ_NODENAME=taurus-rabbit \
  -p 15672:15672 \
  -d \
  rabbitmq:3-management
```

Start Taurus DynamoDB container:

```
docker run \
  --name taurus-dynamodb \
  -e DYNAMODB_PORT=8300 \
  -p 8300:8300 \
  -d \
  taurus-dynamodb:latest
```

Start Taurus container(s):

```
docker run \
  --name taurus \
  --link taurus-rabbit:rabbit \
  -e RABBITMQ_HOST=rabbit \
  -e RABBITMQ_USER=guest \
  -e RABBITMQ_PASSWD=guest \
  --link taurus-mysql:mysql \
  -e MYSQL_HOST=mysql \
  -e MYSQL_USER=root \
  -e MYSQL_PASSWD=taurus \
  --link taurus-dynamodb:dynamodb \
  -e DYNAMODB_HOST=dynamodb \
  -e DYNAMODB_PORT=8300 \
  -e TAURUS_RMQ_METRIC_DEST=rabbit \
  -e TAURUS_RMQ_METRIC_PREFIX=docker \
  -p 8443:443 \
  -p 9001:9001 \
  -d \
  --privileged \
  taurus:latest

docker run \
  --name taurus-collectors \
  --link taurus-rabbit:rabbit \
  -e RABBITMQ_HOST=rabbit \
  -e RABBITMQ_USER=guest \
  -e RABBITMQ_PASSWD=guest \
  --link taurus-mysql:mysql \
  -e MYSQL_HOST=mysql \
  -e MYSQL_USER=root \
  -e MYSQL_PASSWD=taurus \
  --link taurus:taurus \
  -e TAURUS_HTM_SERVER=taurus \
  -e TAURUS_METRIC_COLLECTORS_LOG_DIR=/opt/numenta/taurus.metric_collectors/logs \
  -e TAURUS_TWITTER_ACCESS_TOKEN=${TAURUS_TWITTER_ACCESS_TOKEN} \
  -e TAURUS_TWITTER_ACCESS_TOKEN_SECRET=${TAURUS_TWITTER_ACCESS_TOKEN_SECRET} \
  -e TAURUS_TWITTER_CONSUMER_KEY=${TAURUS_TWITTER_CONSUMER_KEY} \
  -e TAURUS_TWITTER_CONSUMER_SECRET=${TAURUS_TWITTER_CONSUMER_SECRET} \
  -e XIGNITE_API_TOKEN=${XIGNITE_API_TOKEN} \
  -p 8001:8001 \
  -d \
  --privileged \
  taurus.metric_collectors:latest
```

*Note*: You must have `TAURUS_TWITTER_ACCESS_TOKEN`,
`TAURUS_TWITTER_ACCESS_TOKEN_SECRET`, `TAURUS_TWITTER_CONSUMER_KEY`,
`TAURUS_TWITTER_CONSUMER_SECRET`, `XIGNITE_API_TOKEN` which are specific to
your accounts with the respective services set in your environment for the
above command to succeed.

Inspect logs:

```
docker logs --tail=1000 -f taurus
```

*Note*: Supervisor configuration has been modified to log everything to stdout.

At this point, the full Taurus Server application is running in the VM, which
is only exposing the HTTPS interface on port `8443` and the supervisor api on
`9001`.  Should you need to connect to MySQL or Rabbit, you will either need to
modify `config.rb` and reload vagrant to expose those ports, or you may
establish an ssh tunnel using the following command(s).

To exchange keys:

```
vagrant ssh-config | sed -n "s/IdentityFile//gp" | head -n 1 | xargs ssh-add
```

Establish ssh tunnel:

```
vagrant ssh -- -L 3306:0.0.0.0:3306
```

Then, you can connect to localhost on port `3306` with a MySQL client.


FROM numenta/nupic:latest
RUN apt-get install -y libmysqlclient-dev mysql-client
ADD . /opt/numenta/nta.utils
WORKDIR /opt/numenta/nta.utils
ENV PYTHONPATH /usr/local/lib/python2.7/site-packages
RUN python setup.py develop --install-dir=/usr/local/lib/python2.7/site-packages --script-dir=/usr/local/bin

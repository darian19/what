FROM nta.utils:latest
ADD . /opt/numenta/htmengine
WORKDIR /opt/numenta/htmengine
RUN python setup.py develop --install-dir=/usr/local/lib/python2.7/site-packages --script-dir=/usr/local/bin

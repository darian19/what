
events {
    worker_connections 1024;
}
user %(NGINX_USER)s %(NGINX_GROUP)s;

http {
  # Enable gzip compression, if client supports it
  gzip on;
  gzip_buffers 16 8k;
  gzip_comp_level 4;
  gzip_vary on;
  gzip_http_version 1.0;
  gzip_types text/plain image/svg+xml text/css application/javascript text/xml application/xml application/json text/javascript application/octet-stream;

  keepalive_timeout 60;

  include mime.types;

  server {
    # HTTP section

    listen 80;

    add_header "X-UA-Compatible" "IE=edge";

    # Some endpoints require non-secure http access.  Create special-case
    # location directives, and redirect everything else to the https-equivalent
    # endpoint.  Note: = (exact match) and ^~ (prefix match) instruct nginx to
    # stop searching for a match if one is found.
    #
    # See http://wiki.nginx.org/HttpCoreModule#location

    location ^~ /_annotations {
      include nginx-uwsgi.conf;
    }
    location ^~ /_anomalies {
      include nginx-uwsgi.conf;
    }
    location = /_models {
      include nginx-uwsgi.conf;
    }
    location ^~ /_models/data {
      include nginx-uwsgi.conf;
    }
    location ~ /_models/.+/data {
      include nginx-uwsgi.conf;
    }
    location = /_msgs {
      include nginx-uwsgi.conf;
    }
    # In the updater, maintenance.html does an ajax call to /YOMP/embed/charts
    # to determine that the API server is alive. This has to be done over http
    # because Chrome throws an error about our unsigned SSL cert otherwise and
    # the maintenance.html spins forever.
    location = /YOMP/embed/charts {
      include nginx-uwsgi.conf;
    }
    location ^~ /static {
      root %(YOMP_HOME)s;
    }
    location / {
      # Redirect everything not already matched to https equivalent
      return 301 https://$host$request_uri;
    }
  }

  server {
    # HTTPS section

    listen 443;
    server_name localhost;

    add_header "X-UA-Compatible" "IE=edge";

    ssl on;
    ssl_certificate %(NGINX_SSL_CERTIFICATE)s;
    ssl_certificate_key %(NGINX_SSL_CERTIFICATE_KEY)s;

    # Disable SSLv3 to cope with POODLE
    ssl_protocols TLSv1 TLSv1.1 TLSv1.2;

    rewrite ^/YOMP/$ /YOMP permanent;
    rewrite ^/YOMP/mobile /YOMP/complete permanent;

    location ^~ /static {
      root %(YOMP_HOME)s;
    }

    location ^~ /supervisor/ {
      include nginx-supervisord.conf;
    }

    location / {
      include nginx-uwsgi.conf;
    }
  }
}

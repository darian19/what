#  YOMP Configuration

 - Link `YOMP-app` to `/usr/local/YOMP`
 - Link `YOMP-api.conf` to `/etc/nginx/conf.d/YOMP-api.conf`

# SSL Keys

## Why do we include a specific self-signed SSL key in this repository?

Due to strict security requirements, android applications cannot normally open SSL connections to servers using self-signed certificates. Requiring a real certificate before the mobile app becomes functional is a burden to the user, so we embed the certificate from YOMP/conf/ssl in the mobile app as a trusted certificate.

Note that if you change YOMP/conf/ssl/localhost.crt, you will also have to change YOMP-mobile/keys/localhost.crt to match.

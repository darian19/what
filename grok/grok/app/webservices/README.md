YOMP Web API
============


This package contains a WSGI application to interface with YOMP. Its entry point is through the webapp module. 


When debugging, it's sometimes handy to use `curl` to send requests to YOMP API; this example assumes that YOMP is running on localhost and YOMP API key is abcdef:
```
curl -k -u abcdef: https://localhost/_metrics/cloudwatch -X GET
```



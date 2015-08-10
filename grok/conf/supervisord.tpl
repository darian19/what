; Sample supervisor config file.
;
; For more information on the config file, please see:
; http://supervisord.org/configuration.html
;
; Note: shell expansion ("~" or "$HOME") is not supported.  Environment
; variables can be expanded using this syntax: "%(ENV_HOME)s".

[unix_http_server]
file=%%(here)s/../YOMP-supervisor.sock   ; (the path to the socket file)

[inet_http_server]
port=127.0.0.1:9001

[supervisord]
environment=APPLICATION_CONFIG_PATH=%(APPLICATION_CONFIG_PATH)s
pidfile=%%(here)s/../YOMP-supervisord.pid
identifier=YOMP-supervisor
logfile=%%(here)s/../logs/YOMP-supervisord.log
# NOTE: logfile_maxbytes=0 turns off supervisor log rotation to prevent conflict
# with YOMP's higher-level log rotation triggered by crontab
logfile_maxbytes=0
logfile_backups=10
loglevel=info
nodaemon=false
minfds=1024
minprocs=200

[rpcinterface:supervisor]
supervisor.rpcinterface_factory = supervisor.rpcinterface:make_main_rpcinterface

[supervisorctl]
serverurl=http://%(SUPERVISOR_HOST)s:%(SUPERVISOR_PORT)s

;*************** METRIC_COLLECTOR **************
[program:metric_collector]
command=python -m YOMP.app.runtime.metric_collector
process_name=%%(program_name)s_%%(process_num)02d
directory=%%(here)s/..
;user=vagrant
numprocs=1
# Use SIGINT instead of SIGTERM; builtin SIGINT handler in python facilitates
# shutdown of multiprocessing subprocesses and process pools.
stopsignal=INT
stdout_logfile_maxbytes=0
stdout_logfile=logs/metrics_collector.log
redirect_stderr=true

;*************** NOTIFICATION_SERVICE **************
[program:notification_service]
command=python -m YOMP.app.runtime.notification_service
process_name=%%(program_name)s_%%(process_num)02d
directory=%%(here)s/..
;user=vagrant
numprocs=1
stdout_logfile_maxbytes=0
stdout_logfile=logs/notification_service.log
redirect_stderr=true

;*************** YOMP-API **************
[program:YOMP-api]
command=uwsgi --enable-threads --socket 0.0.0.0:19002 --master --vacuum --idle 300 --processes 8 --threads 4 --listen 1024 --module YOMP.app.webservices.webapp
process_name=%%(program_name)s_%%(process_num)02d
directory=%%(here)s/..
;user=vagrant
stdout_logfile_maxbytes=0
stdout_logfile=logs/uwsgi.log
redirect_stderr=true
stopsignal=INT


;*************** YOMP-GROUP **************
[group:YOMP]
programs=metric_collector,notification_service,YOMP-api,aggregator_service

;*************** AGGREGATOR_SERVICE **************
[program:aggregator_service]
command=python -m YOMP.app.runtime.aggregator_service
process_name=%%(program_name)s_%%(process_num)02d
directory=%%(here)s/..
;user=vagrant
numprocs=1
# Use SIGINT instead of SIGTERM; builtin SIGINT handler in python facilitates
# shutdown of multiprocessing subprocesses and process pools.
stopsignal=INT
stdout_logfile_maxbytes=0
stdout_logfile=logs/aggregator_service.log
redirect_stderr=true

[include]
files = ../../htmengine/conf/supervisord-base.conf


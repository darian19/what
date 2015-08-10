# YOMP Application Layer configuration

[debugging]
# Controls whether to log performance profiling information: true or false
profiling = false

# MySQL database connection parameters
[repository]
db = YOMP
host = 127.0.0.1
user = root
passwd =
port = 3306

[admin]
# Allow changes to these Sections of this file
configurable_sections = aws,usertrack,notifications

[web]
base_url =
uwsgi_port = 8080
debug_level = 0

[metric_streamer]
# Exchange to push model results
results_exchange_name = YOMP.model.results
# Max records per batch to stream to model
chunk_size = 1440

[aws]
aws_access_key_id =
aws_secret_access_key =
default_region = %(DEFAULT_EC2_REGION)s

[usertrack]
YOMP_id = %(YOMP_ID)s
optin =
name =
company =
email =

# epoch of last installed update
YOMP_update_epoch = %(YOMP_UPDATE_EPOCH)s

# Send to WUFOO: yes or no
send_to_wufoo = %(YOMP_SEND_TO_WUFOO)s

# Wufoo credentials
wufoo_url = %(WUFOO_URL)s
wufoo_user = %(WUFOO_USER)s

[metric_collector]
# How often to poll metrics for data in seconds
poll_interval = 60
# Metric error grace period seconds after which the metric will be promoted to
# ERROR state if it continues to encounter errors
metric_error_grace_period = 10800

[metric_listener]
# Port to listen on for plaintext protocol messages
plaintext_port = 2003
queue_name = YOMP.metric.custom.data

[security]
apikey =

[notifications]
sender = %(NOTIFICATIONS_SENDER_EMAIL)s
subject = YOMP: Unusual behavior seen on: {instance}
body_default = notification-body-default.tpl
body_custom = notification-body-custom.tpl
aws_access_key_id = %(NOTIFICATIONS_AWS_ACCESS_KEY_ID)s
aws_secret_access_key = %(NOTIFICATIONS_AWS_SECRET_ACCESS_KEY)s

[registration]
subject = Welcome to YOMP!
body = registration-body.tpl

[anomaly_likelihood]
# Minimal sample size for statistic calculation
statistics_min_sample_size=100
# How often to refresh the anomaly statistics in rows
# We refresh once every two hours (ideally we would do this every record)
statistics_refresh_rate=24
# Sample size to be used for the statistic calculation
# We keep a max of one month of history (assumes 5 min metric period)
statistics_sample_size=8640

nta.utils
=========

`nta.utils` is a library implements commonly used patterns in Numenta
applications.

Installation
------------

    python setup.py develop --install-dir=<site-packages in $PYTHONPATH>

- `--install-dir` must specify a location in your PYTHONPATH, typically
  something that ends with "site-packages".  If not specified, system default
  is used.


Environment Variables
---------------------

`AWS_ACCESS_KEY_ID`: The AWS access key; used by `error_reporting.py` for
  sending emails via SES

`AWS_SECRET_ACCESS_KEY`: The AWS secret key; used by `error_reporting.py` for
  sending emails via SES

`ERROR_REPORT_EMAIL_AWS_REGION`: AWS region for SES; used by
  `error_reporting.py` for sending emails via SES

`ERROR_REPORT_EMAIL_SES_ENDPOINT`: AWS SES endpoint for error report email

`ERROR_REPORT_EMAIL_RECIPIENTS`: Recipients of the error report emails. Email
      addresses need to be comma-separated
      Example => recipient1@organization.com, recipient2@organization.com

`ERROR_REPORT_EMAIL_SENDER_ADDRESS`: Sender email address for error report email


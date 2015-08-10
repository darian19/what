YOMP Command Line Interface
===========================

This repository contains the YOMP Command line interface (CLI). `YOMPcli` allows you to easily interact with a YOMP server through the command line including creating instances, etc.

In addition you can use `YOMPcli` to integrate with third party applications.  Included in `YOMPcli` is an integration with Datadog (see [YOMP Integration With Datadog](docs/YOMP-Integration-with-DataDog.pdf) for full details). See more details by running `python -m YOMPcli.datadog --help`.

Installation
------------

Requires: Python (2.6 or greater)

- pip (recommended)

  `pip install YOMPcli`

- easy_install

  `easy_install YOMPcli`

- setup.py

  `python setup.py install`

Usage
-----

YOMP CLI tools provides a single, high-level `YOMP` command, from which
a number of sub-commands can be invoked:

    YOMP [command] [options]

Each command takes `YOMP_SERVER_URL` and `YOMP_API_KEY` as the first two arguments after the command name. However, if you set those two environment variables, you can omit those arguments from the commands.

- `YOMP credentials`

  Use the `YOMP credentials` sub-command to add your AWS credentials to a
  running YOMP server configuration:

      YOMP credentials YOMP_SERVER_URL [options]

  The `YOMP_SERVER_URL` positional argument is required and must be a url to a
  running YOMP server.  For example: https://ec2-AA-BB-CC-DD.us-west-2.compute.amazonaws.com

  You can specify your credentials in one of three ways:

  - Specify `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` CLI options.

    ```
    YOMP credentials YOMP_SERVER_URL --AWS_ACCESS_KEY_ID=... --AWS_SECRET_ACCESS_KEY=...
    ```

  - Read AWS credentials from a specific file using the `-d`, or `--data` CLI
    options.

    ```
    YOMP credentials YOMP_SERVER_URL -d PATH_TO_FILE
    YOMP credentials YOMP_SERVER_URL --data=PATH_TO_FILE
    ```

    You can read from stdin using `-`:

    ```
    YOMP credentials YOMP_SERVER_URL -d - < PATH_TO_FILE
    YOMP credentials YOMP_SERVER_URL --data=- < PATH_TO_FILE
    ```

    The credentials file should be formatted according to this template:

    ```
    AWS_ACCESS_KEY_ID=Your AWS access key ID here
    AWS_SECRET_ACCESS_KEY=Your AWS secret access key here
    ```

  - Use existing boto configuration.

    ```
    YOMP credentials YOMP_SERVER_URL --use-boto
    ```

- `YOMP export`

  Export YOMP model definitions to a file in JSON or YAML format.

      YOMP export [YOMP_SERVER_URL YOMP_API_KEY] [options]

  The `YOMP_SERVER_URL` positional argument is required and must be a url to a
  running YOMP server.  For example: https://ec2-AA-BB-CC-DD.us-west-2.compute.amazonaws.com

  The `YOMP_API_KEY` positional argument is also required, and can be retrieved
  from the web interface of a running YOMP server.

  By default, `YOMP export` prints output to stdout, which can be directed to a
  file:

      YOMP export [YOMP_SERVER_URL YOMP_API_KEY] > file.json

  However, you can optionally specify a file using the `-o` or `--output` CLI
  option:

      YOMP export [YOMP_SERVER_URL YOMP_API_KEY] -o file.json
      YOMP export [YOMP_SERVER_URL YOMP_API_KEY] --output=file.json

  Use the `-y` or `--yaml` CLI flag to save output in YAML format

      YOMP export [YOMP_SERVER_URL YOMP_API_KEY] -y
      YOMP export [YOMP_SERVER_URL YOMP_API_KEY] --yaml

- `YOMP import`

  Import YOMP model definitions into a YOMP server from a local file.

      YOMP import [YOMP_SERVER_URL YOMP_API_KEY] [FILE] [options]

  The `YOMP_SERVER_URL` positional argument is required and must be a url to a
  running YOMP server.  For example: https://ec2-AA-BB-CC-DD.us-west-2.compute.amazonaws.com

  The `YOMP_API_KEY` positional argument is also required, and can be retrieved
  from the web interface of a running YOMP server. The API Key is synonymous with the mobile
  password.

  The `FILE` positional argument is optional, however if it is not specified,
  `YOMP import` will assume `STDIN` if `-d` or `--data` is not specified.  The
  following are equivalent:

      YOMP import [YOMP_SERVER_URL YOMP_API_KEY] file.json
      YOMP import [YOMP_SERVER_URL YOMP_API_KEY] < file.json
      YOMP import [YOMP_SERVER_URL YOMP_API_KEY] -d file.json
      YOMP import [YOMP_SERVER_URL YOMP_API_KEY] --data=file.json

  `YOMP import` supports files in YAML format, if pyyaml is installed and
  available on the system.

- `YOMP (DELETE|GET|POST)`

  Included in the YOMP CLI tool is a lower-level direct API which translates
  CLI options to direct HTTP calls into the YOMP web service.  For example, to
  get all available cloudwatch metrics:

      YOMP GET YOMP_SERVER_URL/_metrics/cloudwatch YOMP_API_KEY

  For `YOMP POST` and `YOMP DELETE`, where request data may be required, such
  data can be specified either via the `-d`, or `--data` CLI option, or
  supplied via STDIN:

      YOMP POST YOMP_SERVER_URL/_models YOMP_API_KEY < model-definition.json
      YOMP POST YOMP_SERVER_URL/_models YOMP_API_KEY -d model-definition.json
      YOMP POST YOMP_SERVER_URL/_models YOMP_API_KEY --data model-definition.json

- `YOMP metrics`

  Manage monitored metrics.

      YOMP metrics (list|unmonitor) [YOMP_SERVER_URL YOMP_API_KEY] [options]

  To get a list of monitored metrics:

      YOMP metrics [YOMP_SERVER_URL YOMP_API_KEY]

  Limiting to monitored metrics for a specific AWS instance:

      YOMP metrics list [YOMP_SERVER_URL YOMP_API_KEY] --instance=INSTANCE_ID --region=REGION --namespace=NAMESPACE

  To unmonitor a metric:

      YOMP metrics unmonitor https://localhost CmHnD --id=METRIC_ID

- `YOMP instances`

  Manage monitored instances.

      YOMP instances (list|unmonitor) [YOMP_SERVER_URL YOMP_API_KEY] [options]

  To get a list of all monitored instances:

      YOMP instances list [YOMP_SERVER_URL YOMP_API_KEY]

  To unmonitor an instance:

      YOMP instances unmonitor [YOMP_SERVER_URL YOMP_API_KEY] --id=INSTANCE_ID

- `YOMP cloudwatch`

  Manage CloudWatch metrics.

      YOMP cloudwatch (metrics|instances) (list|monitor|unmonitor) [YOMP_SERVER_URL YOMP_API_KEY] [options]

  To list available cloudwatch metrics:

      YOMP cloudwatch metrics list [YOMP_SERVER_URL YOMP_API_KEY]

  To filter list of available cloudwatch metrics by instance id:

      YOMP cloudwatch metrics list [YOMP_SERVER_URL YOMP_API_KEY] --instance=INSTANCE_ID

  To monitor a metric (example):

      YOMP cloudwatch metrics monitor [YOMP_SERVER_URL YOMP_API_KEY] \
        --metric=CPUUtilization \
        --namespace=AWS/EC2 \
        --region=us-west-2 \
        --dimensions InstanceId i-abc123

  To monitor an instance (example):

      YOMP cloudwatch instances monitor [YOMP_SERVER_URL YOMP_API_KEY] \
        --namespace=AWS/EC2 \
        --region=us-west-2 \
        --instance=i-abc123

  To unmonitor a metric (example):

      YOMP cloudwatch metrics unmonitor [YOMP_SERVER_URL YOMP_API_KEY] \
        --metric=CPUUtilization \
        --namespace=AWS/EC2 \
        --region=us-west-2 \
        --dimensions InstanceId i-abc123

  To unmonitor an instance (example):

      YOMP cloudwatch instances unmonitor [YOMP_SERVER_URL YOMP_API_KEY] \
        --namespace=AWS/EC2 \
        --region=us-west-2 \
        --instance=i-abc123

- `YOMP custom`

  Manage custom metrics.

  To list available custom metrics:

      YOMP custom metrics list [YOMP_SERVER_URL YOMP_API_KEY]

  To monitor a custom metric:

      YOMP custom metrics monitor [YOMP_SERVER_URL YOMP_API_KEY] --id=METRIC_ID

  To unmonitor a custom metric:

      YOMP custom metrics unmonitor [YOMP_SERVER_URL YOMP_API_KEY] --name=METRIC_NAME

- `YOMP autostacks`

  Manage autostacks.

  To create an autostack:

      YOMP autostacks stacks create [YOMP_SERVER_URL YOMP_API_KEY] --name=NAME --region=REGION --filters='{"tag:FILTER_NAME": ["FILTER_VALUE"]}'

  You can use any AWS tag for FILTER_NAME. The FILTER_VALUE is an AWS-specific
  wildcard, not a full-fledged regular expression. * matches any number of characters
  and ? matches any single character. The filter name and value are both
  case-sensitive.

  For example, "jenkins-*" and "jenkins-??????" both match "jenkins-master".

  You can use any AWS tag for the first component of a filter, though for
  optimal performance we recommend that the first tag/value pair specified be
  the one that eliminates the most instances. Because AWS only supports OR
  operations at this time, we have to implement the AND (intersection) operation
  locally. Our implementation sends the first tag/value to AWS, gets all the
  matching instances, and then filters them against the remaining tag/value
  filters locally.

  This does not create any metrics for the new autostack. You must create metrics
  for the new autostack with YOMP autostacks metrics add (see below)

  To preview an autostack:

      YOMP autostacks stacks create [YOMP_SERVER_URL YOMP_API_KEY] --preview --region=REGION --filters='{"tag:FILTER_NAME": ["FILTER_VALUE"]}'

  To list AutoStacks:

      YOMP autostacks stacks list [YOMP_SERVER_URL YOMP_API_KEY]

  To delete an AutoStack:

      YOMP autostacks stacks delete [YOMP_SERVER_URL YOMP_API_KEY] --name=STACK_NAME --region=REGION

  or:

      YOMP autostacks stacks delete [YOMP_SERVER_URL YOMP_API_KEY] --id=STACK_ID

  To add metric type(s) monitored by an AutoStack:

      YOMP autostacks metrics add [YOMP_SERVER_URL YOMP_API_KEY] --name=STACK_NAME --region=REGION --metric_namespace=METRIC_NAMESPACE --metric_name=METRIC_NAME

  or:

      YOMP autostacks metrics add [YOMP_SERVER_URL YOMP_API_KEY] --id=STACK_ID --metric_namespace=METRIC_NAMESPACE --metric_name=METRIC_NAME

  To list metric type(s) monitored by an AutoStack:

      YOMP autostacks metrics list [YOMP_SERVER_URL YOMP_API_KEY] --name=STACK_NAME --region=REGION

  or:

      YOMP autostacks metrics list [YOMP_SERVER_URL YOMP_API_KEY] --id=STACK_ID

  To remove metric type(s) monitored by an AutoStack:

      YOMP autostacks metrics remove [YOMP_SERVER_URL YOMP_API_KEY] --name=STACK_NAME --region=REGION --metric_id=METRIC_ID

  or:

      YOMP autostacks metrics remove [YOMP_SERVER_URL YOMP_API_KEY] --id=STACK_ID --metric_id=METRIC_ID

  To list EC2 Instances associated with an AutoStack(s):

      YOMP autostacks instances list [YOMP_SERVER_URL YOMP_API_KEY] --name=STACK_NAME --region=REGION

  or:

      YOMP autostacks instances list [YOMP_SERVER_URL YOMP_API_KEY] --id=STACK_ID

Note to developers
------------------

To add a command, create a python module in
[YOMPcli/commands/](YOMPcli/commands) with a `handle()` function which accepts
two arguments: `options`, and `args`.  Register the command by importing the
module in [YOMPcli/commands/\_\_init\_\_.py](YOMPcli/commands/__init__.py) and
adding it to `__all__`.


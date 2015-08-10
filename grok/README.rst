====
YOMP
====

YOMP is an application for monitoring IT infrastructure and notifying on
anomalous behavior.

Setup
=====

Dependencies:

* `MySQL <http://dev.mysql.com/downloads/mysql/>`_
* `RabbitMQ <http://www.rabbitmq.com/download.html>`_
* `nGinx <http://nginx.org/en/download.html>`_
* `NuPIC <https://YOMPhub.com/numenta/nupic>`_

::

    cd ~/nta/numenta-apps

**NOTE:** Do not use sudo with pip.

Python dependencies are documented in requirements.txt and installed
automatically with YOMP.

::

    ./install-YOMP.sh <site-packages in $PYTHONPATH> <somewhere in $PATH>

The first directory can be any directory on your `PYTHONPATH`. The second directory can be any directory on your `PATH`.

- e.g., `./install-YOMP.sh /opt/numenta/anaconda/lib/python2.7/site-packages/ /opt/numenta/anaconda/bin/`


Config
======

Bootstrap your YOMP configuration files and initialize the database:
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

*NOTE:* Remember to set APPLICATION_CONFIG_PATH environment variable to the directory where
generated YOMP configuration files should be stored by `python setup.py init`. If not set,
it presently defaults to the location of YOMP configuraiton template files (e.g., `YOMP/conf/`)

You'll need to install/start MySQL server and RabbitMQ server prior to running `setup.py init`

::

    python setup.py init


Review your YOMP configuration file and make changes as necessary.


Common YOMP Environment Variables
=================================

`APPLICATION_CONFIG_PATH`: directory path where active YOMP application
configuration files are located

`AWS_ACCESS_KEY_ID`: The AWS access key

`AWS_SECRET_ACCESS_KEY`: The AWS secret key

`YOMP_API_KEY`: If defined, YOMP's `setup.py init` uses its value to initialize
the `[security] apikey` setting in YOMP's `application.conf`; if not defined,
YOMP's `setup.py init` will generate the API key automatically.

`YOMP_HOME`: the directory path of the parent directory of the YOMP package
directory; the pipeline code relies on this environment variable being set. The
application code falls back to a computed path if `YOMP_HOME` is not in the
environment.

`YOMP_LOG_DIR`: Directory path where application logs should be stored;
application code falls back to the parent directory of YOMP's package directory.


YOMP Environment Variables Specific to the Build System
=======================================================

`JOB_NAME`: Name of the build job; used by build pipeline and
`behavioral_tests_driver`;

`BUILD_NUMBER`: This is set automatically by Jenkins to manage the
workspace.  If this is not set, the current SHA will be used by the pipeline.

`WORKSPACE`: This is an internal use parameter that is automatically set by
Jenkins and _**should not be populated manually**_. It defines where on the
machine Jenkins will checkout the repository and run the pipeline.

`BUILD_WORKSPACE`: This is an optional parameter. If pipeline does not find
`BUILD_WORKSPACE` it will create one for you inside `WORKSPACE` as follows:
`${WORKSPACE}/${BUILD_NUMBER}`. Setting this env var ensures you build in a
specific location if needed.

`JENKINS_HOME`: This is automatically set by Jenkins and should not be populated
manually.

`PRODUCTS`: directory path of the `products` tree; used by the build pipeline

`LOG_UPLOADER_S3_ACCESS_KEY_ID`: AWS Access Key for uploading log files

`LOG_UPLOADER_S3_SECRET_ACCESS_KEY`: AWS Secret Access Key for uploading log files

`WUFOO_URL`: Wufoo form URL

`WUFOO_USER`: User token to be able to submit data to Wufoo

`NOTIFICATIONS_AWS_ACCESS_KEY_ID`: AWS Access Key for sending email notifications

`NOTIFICATIONS_AWS_SECRET_ACCESS_KEY`: AWS Secret Access Key for sending email notifcations

`NOTIFICATIONS_SENDER_EMAIL`: Email address from which to send email notifications

`REMOTE`: Git remote to pull from, generally https://YOMPhub.com/Numenta/numenta-apps

`BRANCH`: Git branch to checkout, generally master

`COMMIT_SHA`: Git commit SHA to reset to, generally master


Run
===

Start MySQL
~~~~~~~~~~~

Individual configurations may vary.  Be sure to start MySQL however best works
with the installation path you followed.

Start RabbitMQ
~~~~~~~~~~~~~~

::

    rabbitmq-server -detached


Reset RabbitMQ
~~~~~~~~~~~~~~
If you have an old copy of YOMP then you need to clean up RabbitMQ queues.

::

    rabbitmqctl stop_app
    rabbitmqctl reset
    rabbitmqctl start_app


Start nGinx
~~~~~~~~~~~

::

    sudo nginx -p . -c conf/YOMP-api.conf

Start YOMP Services
~~~~~~~~~~~~~~~~~~~

::

    supervisord -c conf/supervisord.conf

Use YOMP
~~~~~~~~

- Web App:

  - Initial Setup: https://localhost/YOMP/welcome
  - Home: https://localhost/YOMP

- Supervisor:

  - Direct: http://localhost:9001
  - HTTPS:  https://localhost/supervisor

Test
====

Setup AWS Credentials for Integration Tests
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

AWS Credentials needs to be setup for YOMP application before running integration tests. You can either use the YOMP Web UI to set those up or use YOMP CLI to do the same.

Specify AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY CLI options.

::

    YOMP credentials YOMP_SERVER_URL --AWS_ACCESS_KEY_ID=... --AWS_SECRET_ACCESS_KEY=...


Set AWS credentials from a specific file using the -d, or --data CLI options.

::

    YOMP credentials YOMP_SERVER_URL -d PATH_TO_FILE
    YOMP credentials YOMP_SERVER_URL --data=PATH_TO_FILE


For more details refer YOMP CLI readme.


Python
~~~~~~

Run Python unit tests:

::

    ./run_tests.sh -l py

Run Python integration tests:

::

    # Prepare for integration tests by restarting supervisor
    # and initializing.
    supervisorctl shutdown
    python setup.py init
    ./bin/set_edition.py standard
    ./bin/update_quota.py
    supervisord -c conf/supervisord.conf
    # Run with --num=X option to multithread. (TODO: MER-2177)
    ./run_tests.sh -l py -i

Javascript
~~~~~~~~~~

Install `NodeJS <http://nodejs.org/>`_ and `NPM <https://npmjs.org/>`_.

If using `homebrew <http://brew.sh/>`_:

::

    brew install node

Install node dev/test npm module dependencies:

::

    npm install

Run Javascript tests locally on dev laptop (Mac OS X):

::

    open tests/js/unit/*.html

Run Javascript tests on SauceLabs Browser testing cloud (logs stored in `/tmp`):

::

    export SAUCE_USERNAME=<username>
    export SAUCE_ACCESS_KEY=<accesskey>
    ./run_tests.sh -l js


Documentation
=============

Complete documentation can be built using `Sphinx <http://sphinx.pocoo.org/>`_:

::

    python setup.py build_sphinx

Once built, docs will be in ``build/sphinx/html``.  Periodically, you should run
``sphinx-apidoc`` and commit new .rst files that it creates:

::

    sphinx-apidoc -f -o docs/ YOMP
    YOMP add docs/*.rst
    YOMP commit

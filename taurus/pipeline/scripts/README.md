A set of helper scripts are provided to automate the process of initializing,
updating, and refreshing a pair of Taurus Server and Taurus Metric Collector
instances:
- `initialize-remote-taurus-servers.sh`
- `update-remote-taurus-servers.sh`
- `refresh-remote-taurus-servers.sh`

Usage
-----

The above scripts make several assumptions about the state of the instances
in use.  In particular, that a baseline set of requirements are satisfied and
that the instances are capable of being used without further manual
modification.  Internally, Numenta uses some tooling to launch and configure
AWS EC2 instances that meet the requirements.

Initialization
--------------

Run `./initialize-remote-taurus-servers.sh -h` for a comprehensive list of
required environment variables needed for initializing a pair of servers to run
Taurus.

To initialize a fresh pair of instances, ensure that your environment has been
set up to specify all of the required environment variables, then run:

        ./initialize-remote-taurus-servers.sh

For a verbose, debug version, also set `DEBUG` environment variable to `1`:

        DEBUG=1 ./initialize-remote-taurus-servers.sh

Updating Taurus
---------------

To update a previously initialized running pair of instances, ensure that your
environment has been set up to specify all of the required environment
variables, then run:

        ./update-remote-taurus-servers.sh

For a verbose, debug version, also set `DEBUG` environment variable to `1`:

        DEBUG=1 ./update-remote-taurus-servers.sh

`update-remote-taurus-servers.sh` will run unit and integration tests.

Refreshing Taurus
-----------------

To completely refresh Taurus, including clearing out metrics and model
checkpoints, ensure that your environment has been set up to specify all of the
required environment variables, then run:

        ./refresh-remote-taurus-servers.sh

For a verbose, debug version, also set `DEBUG` environment variable to `1`:

        DEBUG=1 ./refresh-remote-taurus-servers.sh

`refresh-remote-taurus-servers.sh` will run unit and integration tests.

Design Philosophy
-----------------

The scripts herein comprise simple, single-file utilities for the
initialization, and update of a functional pair of remote Taurus Metric
Collector, and Taurus Server instances.  The design of which are informed by
the following principles:

### Compute resources are ephemeral

It is relatively trivial to provision, launch, and configure server instances
on-demand.  These scripts are intended to be used in a continuous integration,
and continuous deployment workflow wherein code is updated and tests executed
automatically upon changes to the source repository.  The scripts themselves
are straight-forward, and take an unopinionated approach to execution.  Little
attempt is made to recover an instance from a failed state, either from the
result of a failure in the update process, tests, or intermittent failures.  If
something goes wrong, a failed pair of instances should be replaced with a
fresh pair of instances, or the failed instance remediated manually.

### Automate everything

Humans are prone to mistakes, computers less so.  This should be obvious.

### Keep it simple

If you take a look at the sources, you might notice a remarkable similarity
between `initialize-remote-taurus-servers.sh`,
`update-remote-taurus-servers.sh`, and `refresh-remote-taurus-servers.sh`.
While it goes against the Don't Repeat Yourself (DRY) mantra to duplicate,
rather than share, code between the two scripts.  The scripts themselves stand
on their own as single, plain-text files with no outside dependencies, and can
be read as they are executed: linearly, from top to bottom.  There is also a
single nexus of configuration (the environment), from which an installation may
be reproduced, or altered deterministically.  An entire environment setup may
exist in a single revision-control-system-, and
configuration-management-system-, friendly text file that may be `source`ed in
a shell before the script(s) are executed.


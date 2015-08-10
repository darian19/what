# taurus.monitors

`taurus.monitors` implements several monitors of the Taurus infrastructure and
a supporting database.

## Installation

### Configuration files

The configuration files for production reside in `conf/`.  It is recommended
that you copy and rename this directory so that you may make the required
local changes without conflicts:

    cp -r conf conf-user

Alternatively, the configureation files' path can be overidden using the 
TAURUS_MONITORS_DB_CONFIG_PATH environment variable.

### First, install `nta.utils`.  Then, to install `taurus.monitors`:

    python setup.py develop --install-dir=<site-packages in $PYTHONPATH> --script-dir=<somewhere in $PATH>

- `--install-dir` must specify a location in your PYTHONPATH, typically
  something that ends with "site-packages".  If not specified, system default
  is used.
- `--script-dir` must specify a location in your PATH.  The Taurus installation
  defines and installs some CLI utilities into this location.  If not
  specified, the generated scripts go into the location specified in
  `--install-dir`.

### Set up `monitorsdb` sql database connection

1. The configuration in `conf/taurus-monitors-sqldb.conf` defaults to 
host=localhost with the default user/password for mysql. To override mysql 
host, username and password, use the following command, substituting the 
appropriate strings for HOST, USER and PASSWORD:
```
    >>> taurus-set-monitorsdb-login --host=HOST --user=USER --password=PASSWORD
```

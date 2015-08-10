`collectorsdb` requires mysql login configuration to be set up. The configuration is via `collectors-sqldb.conf` configuration object. This is accomplished via `set_collectorsdb_login.py`.

The script `set_collectorsdb_login.py` (also exposed as console script `taurus-set-collectorsdb-login` by the package's `setup.py`) applies the given mysql login information as overrides for `collectors-sqldb.conf`.

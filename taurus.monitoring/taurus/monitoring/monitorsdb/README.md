`monitorsdb` requires mysql login configuration to be set up. The configuration 
is via `taurus-monitors-sqldb.conf` configuration object. This is accomplished 
via `set_monitorsdb_login.py`.

The script `set_monitorsdb_login.py` (also exposed as console script 
`taurus-set-monitorsdb-login` by the package's `setup.py`) applies the given 
mysql login information as overrides for `taurus-monitors-sqldb.conf`.

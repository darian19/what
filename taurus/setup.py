from setuptools import setup, find_packages

requirements = map(str.strip, open("requirements.txt").readlines())

# TODO: TAUR-1209 rename to "taurus.engine"
name = "taurus"

setup(
  name = name,
  version = "0.4.0",
  description = "Taurus Server",
  namespace_packages = ["taurus"], # TODO: TAUR-1209 use name var
  packages = find_packages(),
  install_requires = requirements,
  entry_points = {
    # TODO: TAUR-1209 remove ".engine" with updated name var
    "console_scripts": [
      "taurus-create-db = %s.engine.repository:reset" % name,
      ("taurus-set-dynamodb = "
       "%s.engine.runtime.dynamodb.set_dynamodb_credentials:main") % name,
      "taurus-set-rabbitmq = %s.engine.set_rabbitmq_login:main" % name,
      "taurus-set-sql-login = %s.engine.repository.set_sql_login:main" % name
    ]
  }
)

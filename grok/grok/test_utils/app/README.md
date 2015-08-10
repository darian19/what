**REPOSITORY DATABASE PATCH EXAMPLE (UPDATED FOR SQLALCHEMY)**

Create a temporary fresh database and instruct the SQLAlchemy engine to use it.
_Note: currently forces BOTH SQLAlchemy and DAO to use the temporary db as
refactoring is completed._

A ManagedTempRepository instance may be used as a Context Manager or function
decorator. The example below is for Context Manager.

```python
import subprocess
from YOMP.test_utils.app.sqlalchemy_test_utils import \
    ManagedTempRepository, getAllDatabaseNames
import YOMP.app

print "all databases BEFORE PATCH:", getAllDatabaseNames()

with ManagedTempRepository("MyTest") as repo:
  print "all databases IN PATCH:", getAllDatabaseNames()

  print "repository db in-proc:", YOMP.app.config.get("repository", "db")

  p = subprocess.Popen(["python", "-c", "import YOMP.app; print 'repository db in subprocess:', "
                        "YOMP.app.config.get('repository', 'db')"])
  returnCode = p.wait()


print "all databases AFTER PATCH:", getAllDatabaseNames()
```

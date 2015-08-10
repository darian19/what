**YOMP CONFIGURATION PATCH: ConfigAttributePatch**

Override configuration settings in-proc and of child processes. An instance of
ConfigAttributePatch may be used as a decorator, class decorator or Context
Manager to patch existing configuration attribute values.

*Context Manager Example:*
```python
with ConfigAttributePatch(
   YOMP.app.config.CONFIG_NAME,
   (("aws", "aws_access_key_id", os.environ["AWS_ACCESS_KEY_ID"]),
   ("aws", "aws_secret_access_key", os.environ["AWS_SECRET_ACCESS_KEY"]))):
  <do test logic in the context of the patched config attributes>
```

*Function Decorator Example:*
```python
@ConfigAttributePatch(
   YOMP.app.config.CONFIG_NAME,
   (("aws", "aws_access_key_id", os.environ["AWS_ACCESS_KEY_ID"]),
   ("aws", "aws_secret_access_key", os.environ["AWS_SECRET_ACCESS_KEY"])))
def testSomething(self):
  <do test logic in the context of the patched config attributes>
```

*Class Decorator Example:*
```python
@ConfigAttributePatch(
   YOMP.app.config.CONFIG_NAME,
   (("aws", "aws_access_key_id", os.environ["AWS_ACCESS_KEY_ID"]),
   ("aws", "aws_secret_access_key", os.environ["AWS_SECRET_ACCESS_KEY"])))
class MyTestCase(unittest.TestCase):
  def testSomething(self):
    <do test logic in the context of the patched config attributes>

  def testSomethingElse(self):
    <do test logic in the context of the patched config attributes>
```


*In-proc*

``` python
from nta.utils.test_utils.config_test_utils import ConfigAttributePatch

from nta.utils.config import Config
config = Config("application.conf")

print "poll_interval:", config.get("metric_collector", "poll_interval")
print "chunk_size:", config.get("metric_collector", "chunk_size")


with ConfigAttributePatch("application.conf",
                            (("metric_collector", "poll_interval", "0.001"),
                             ("metric_collector", "chunk_size", "5"))):
  print "poll_interval:", config.get("metric_collector", "poll_interval")
  print "chunk_size:", config.get("metric_collector", "chunk_size")


print "poll_interval:", config.get("metric_collector", "poll_interval")
print "chunk_size:", config.get("metric_collector", "chunk_size")
```


*Subprocess*

``` python
from nta.utils.test_utils.config_test_utils import ConfigAttributePatch
import subprocess

with ConfigAttributePatch("application.conf",
                            (("metric_collector", "poll_interval", "999"),)):
    p = subprocess.Popen(["python", "-c", "import YOMP.app; print 'poll_interval in subprocess:', "
                         "YOMP.app.config.get('metric_collector', 'poll_interval')"])
    returnCode = p.wait()
```

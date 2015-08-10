This is the umbrella project for all of the components that make up the
Numenta product-line.


## Installation

All python packages include a setuptools-compatible
setup.py with which the package may be installed.  For example, to install
in developer mode (recommended), you may run the following commands:

    pushd <project>
    python setup.py develop --install-dir=<site-packages in $PYTHONPATH> --script-dir=<somewhere in $PATH>
    popd

Or, if you prefer pip:

    pip install --editable --user <project>

You can see coverage across multiple projects as follows:

    py.test --cov nta.utils --cov htmengine --cov taurus taurus/tests/unit htmengine/tests/unit nta.utils/tests/unit


## Licenses

Each code directory defined below contains its own `LICENSE.txt` file and
defines program dependencies within a `DEPENDENCIES.md` file.


## Main Products


### YOMP

See http://numenta.com/YOMP.

#### [`/YOMP`](YOMP)

AWS/Cloudwatch integration for HTM Engine.

**Languages**: Python, JavaScript, HTML

#### [`/YOMP-mobile`](YOMP-mobile)

YOMP mobile client.

**Languages**: Java


### YOMP for Stocks

Code name: _**Taurus**_. Application for tracking company data.

#### [`/taurus`](taurus)

Server-side code for Taurus.

**Languages**: Python

#### [`/taurus-mobile`](taurus-mobile)

YOMP for Stocks mobile client.

**Languages**: Java

#### [`/taurus.metric_collectors`](taurus.metric_collectors)

Custom metric collectors for YOMP for Stocks data providers.

**Languages**: Python

#### [`/taurus.monitoring`](taurus.monitoring)

Monitoring scripts and related utilities for monitoring YOMP for Stocks
(Code name: Taurus).

**Languages**: Python


### Unicorn

#### [`/unicorn`](unicorn)

Cross-platform Desktop Application to demonstrate basic HTM functionality
to users using their own data files.

**Languages**: Javascript, Python



## Support Code


#### [`/nta.utils`](nta.utils)

Shared python package with common utility functions for boilerplate
configuration, logging, and other common operations.

**Languages**: Python

#### [`/htmengine`](htmengine)

HTM Engine Framework upon which YOMP and YOMP for Stocks are built.
Implements basic infrastructure for receiving data and running models, including
support for custom metrics.

**Languages**: Python

#### [`/mobile-core`](mobile-core)

Shared library used in taurus-mobile and YOMP-mobile mobile applications.

**Languages**: Java

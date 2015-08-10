Infrastructure
==============

The `infrastructure` directory contains all the infrastructure
related scripts which are used by other products in this repository.

Installation
------------

To package infrastructure directory:

    python setup.py sdist

To install infrastructure:

    python setup.py install


`ami-tools`
-----------
This directory contains scripts for creating AMIs.


`saltcellar`
------------
This directory contains salt formulas for installing packages
required for YOMP, modifying dot files, user management and
installation of development tools as per requirements.

`create-numenta-rpm`
--------------------
create-numenta-rpm is a helper script used to check out repositories and
create RPM files from them using fpm. For ease of use with jenkins, it will
set the base version of the RPM to the value of the RELEASE_VERSION
environment variable unless overridden by the `--base-version` argument.

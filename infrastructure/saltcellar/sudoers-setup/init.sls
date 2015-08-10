#
# Module: sudoers-setup
#
# Copyright (C) 2015 Numenta, Inc.
#
# All rights reserved - Do Not Redistribute
#
#
sudo:
  pkg:
    - installed

/etc/sudoers.d:
  file.directory:
    - user: root
    - group: root
    - mode: 750

# Install our sudoers file
/etc/sudoers:
  file.managed:
    - source: salt://sudoers-setup/files/sudoers
    - mode: 0440
    - user: root
    - group: root

# Grant ec2-user privilegs
/etc/sudoers.d/ec2-user:
  file.managed:
    - source: salt://sudoers-setup/files/ec2-user
    - mode: 0440
    - user: root
    - group: root
    - require:
      - file: /etc/sudoers.d

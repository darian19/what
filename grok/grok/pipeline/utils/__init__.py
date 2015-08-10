# ----------------------------------------------------------------------
# Numenta Platform for Intelligent Computing (NuPIC)
# Copyright (C) 2015, Numenta, Inc.  Unless you have purchased from
# Numenta, Inc. a separate commercial license for this software code, the
# following terms and conditions apply:
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 3 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see http://www.gnu.org/licenses.
#
# http://numenta.org/licenses/
# ----------------------------------------------------------------------



def getGithubUserName(remote):
  """
    This method is used to get the YOMPhub username specific to the fork.
    Hence we could have username in the name of rpm to
    differentiate developer rpm's and YOMPSolutions rpm's
    for eg: getGithubUserName("YOMP@YOMPhub.com:YOMPSolutions/YOMP.YOMP"),
    will return YOMPSolutions.

    :param remote: GitHub remote url.

    :returns: A `String` representing the GH username
    :rtype: string
  """
  userName = remote.split(":")[1]
  return userName.split("/")[0].lower()

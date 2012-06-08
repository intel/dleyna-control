#!/usr/bin/env python

# media-service-demo
#
# Copyright (C) 2012 Intel Corporation. All rights reserved.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms and conditions of the GNU Lesser General Public License,
# version 2.1, as published by the Free Software Foundation.
#
# This program is distributed in the hope it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License
# for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin St - Fifth Floor, Boston, MA 02110-1301 USA.
#
# Mark Ryan <mark.d.ryan@intel.com>
#

from distutils.core import setup
from distutils.command.install_data import install_data

class MSDInstallData(install_data):

    def finalize_options(self):
        self.set_undefined_options('install', ('install_lib', 'install_dir'))
        install_data.finalize_options(self)

setup(name = "msd",
      version = "0.0.1",
      description = "Test DMP to demonstrate features of media-service-upnp",
      author = "Mark Ryan",
      author_email = "mark.d.ryan@intel.com",
      url = "https://01.org/dleyna/about",
      license = "http://www.gnu.org/licenses/lgpl-2.1.html",
      scripts = ['src/media-service-demo.py'],
      package_dir={'msd': 'src/msd'},
      packages = [ "msd" ],
      data_files = [ ("msd" , ["AUTHORS", "README", "ChangeLog", "COPYING"]) ],
      cmdclass = { 'install_data' : MSDInstallData })

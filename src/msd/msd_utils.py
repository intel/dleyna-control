# dleyna-control
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

import tempfile
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
import urllib2
import os

def image_from_file(url):
    tmpfile = tempfile.NamedTemporaryFile(delete=False)
    tmpFileName = tmpfile.name
    image = None
    try:
        with tmpfile:
            message = urllib2.urlopen(url, None, 15)
            tmpfile.write(message.read())
        image = Gtk.Image()
        image.set_from_file(tmpfile.name)
    finally:
        os.unlink(tmpFileName)

    return image

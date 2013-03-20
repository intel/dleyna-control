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
# Jussi Kukkonen <jussi.kukkonen@intel.com>
#

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import GdkPixbuf, Gio

# Loads a pixbuf from given url, calls callback() when pixbuf is ready.
# This should ideally be implemented by calling GFile.read_async() and
# then GInputStream.read_async() multiple times, feeding the data to
# PixbufLoader gradually. Unfortunately GInputStream API is not fully
# usable through gobject-introspection yet.
class PixbufAsyncLoader(object):
    def __on_load_contents(self, image_file, result, userdata):
        try:
            success, buf, etag = image_file.load_contents_finish(result)
            if success:
                loader = GdkPixbuf.PixbufLoader()
                loader.write(buf)
                loader.close()
                self.__callback (loader.get_pixbuf(), userdata)
        except Exception as err:
            print "Failed to load image %s: %s" % (image_file.get_uri(),
                                                   err)

    def __init__(self, url, callback, userdata=None):
        self.__callback = callback
        img_file = Gio.File.new_for_uri(url)
        img_file.load_contents_async(None, self.__on_load_contents,
                                     userdata)

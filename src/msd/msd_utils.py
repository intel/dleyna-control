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

import pygtk
pygtk.require('2.0')
import gtk
import gio
import gobject

# loads a pixbuf from given url, calls callback() when pixbuf is ready
class PixbufAsyncLoader():
    def __on_stream_read(self, stream, result):
        try:
            buf = stream.read_finish(result)
            if buf:
                self.__loader.write (buf)
                stream.read_async(10000, self.__on_stream_read)
            else:
                self.__loader.close ()
                self.__callback (self.__loader.get_pixbuf(), self.__userdata)
        except gobject.GError as err:
            print "Failed to load image: %s" % err.message
            pass

    def __on_file_read(self, image_file, result):
        try:
            stream = image_file.read_finish(result)
            stream.read_async(10000, self.__on_stream_read)
            self.__loader = gtk.gdk.PixbufLoader()
        except gobject.GError as err:
            print "Failed to load image '%s': %s" % (image_file.get_uri(),
                                                     err.message)
            pass

    def __init__(self, url, callback, userdata=None):
        self.__callback = callback
        self.__userdata = userdata
        img_file = gio.File(uri=url)
        img_file.read_async(self.__on_file_read)

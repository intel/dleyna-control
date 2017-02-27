#!/usr/bin/env python

# dleyna-control
#
# Copyright (C) 2012-2017 Intel Corporation. All rights reserved.
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

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gst', '1.0')
from gi.repository import GObject, Gtk, Gst
import dbus
import dbus.service
import dbus.mainloop.glib
import signal

from msd.msd_main_window import *

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    GObject.threads_init()
    Gst.init(None)
    try:
        del os.environ["http_proxy"];
    except Exception, e:
        pass
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    state = State()
    main_window = MainWindow(state)
    Gtk.main()

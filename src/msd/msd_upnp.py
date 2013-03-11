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

from msd_utils import *
import dbus
import os

DLEYNA_SERVER_DBUS_NAME = 'com.intel.dleyna-server'

class MediaObject(object):

    def __init__(self, path):
        obj = dbus.SessionBus().get_object(DLEYNA_SERVER_DBUS_NAME, path)
        self.__propsIF = dbus.Interface(obj,
                                        'org.freedesktop.DBus.Properties')
    def get_prop(self, prop_name, iface = ""):
        return self.__propsIF.Get(iface, prop_name)

class Container(MediaObject):

    def __init__(self, path):
        MediaObject.__init__(self, path)
        obj = dbus.SessionBus().get_object(DLEYNA_SERVER_DBUS_NAME, path)
        self.__containerIF = dbus.Interface(obj,
                                            'org.gnome.UPnP.MediaContainer2')

    def search(self, query, offset, count, fltr, sort="", on_reply=None, on_error=None):
        return self.__containerIF.SearchObjectsEx(query, offset, count, fltr,
                                                  sort,
                                                  reply_handler=on_reply,
                                                  error_handler=on_error)

    def list_children(self, offset, count, fltr, sort="", on_reply=None, on_error=None):
        return self.__containerIF.ListChildrenEx(offset, count, fltr, sort,
                                                 reply_handler=on_reply,
                                                 error_handler=on_error)

class Server (object):
    def __init__(self, path):
        server = MediaObject(path)

        self.path = path
        self.name = server.get_prop("FriendlyName");

        try:
            icon_url = server.get_prop("IconURL");
            self.icon = image_from_file(icon_url);
        except:
            self.icon =  None

        try:
            self.__sort_caps = server.get_prop("SortCaps");
        except:
            self.__sort_caps =  []
        self.__sort_all = "*" in self.__sort_caps

    def has_sort_capability (self, cap):
        return self.__sort_all or cap in self.__sort_caps


class State(object):

    def __on_get_servers_reply (self, servers):
        for path in servers:
            self.__found_server(path)

    def __on_get_servers_error (self, error):
        print "Manager.GetServers() failed: %s" % error

    def __found_server(self, path):
        if not path in self.__servers:
            try:
                self.__servers[path] = Server(path)
                if self.__found_server_cb:
                    self.__found_server_cb(path)
            finally:
                pass

    def __lost_server(self, path):
        if path in self.__servers:
            del self.__servers[path]
            if self.__lost_server_cb:
                self.__lost_server_cb(path)

    def __init__(self):
        obj = dbus.SessionBus().get_object(DLEYNA_SERVER_DBUS_NAME,
                                           '/com/intel/dLeynaServer')
        self.__manager = dbus.Interface(obj,
                                        'com.intel.dLeynaServer.Manager')
        self.__servers = {}
        self.__found_server_cb = None
        self.__lost_server_cb = None

        self.__manager.connect_to_signal("FoundServer", self.__found_server)
        self.__manager.connect_to_signal("LostServer", self.__lost_server)
        self.__manager.GetServers(reply_handler=self.__on_get_servers_reply,
                                  error_handler=self.__on_get_servers_error)

    def set_lost_server_cb(self, callback):
        self.__lost_server_cb = callback

    def set_found_server_cb(self, callback):
        self.__found_server_cb = callback

    def get_server_list(self):
        return self.__servers

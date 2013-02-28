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

    def list_children(self, offset, count, fltr, sort=""):
        return self.__containerIF.ListChildrenEx(offset, count, fltr, sort)

class State(object):

    @staticmethod
    def __create_server_tuple(path):
        server = MediaObject(path)
        folderName = server.get_prop("FriendlyName");

        try:
            icon_url = server.get_prop("IconURL");
            image = image_from_file(icon_url)
        except Exception:
            image = None

        return (folderName, image)

    def __init_servers(self):
        for i in self.__manager.GetServers():
            try:
                self.__servers[i] = State.__create_server_tuple(i)
            except dbus.exceptions.DBusException:
                pass

    def found_server(self, path):
        if not path in self.__servers:
            try:
                self.__servers[path] = State.__create_server_tuple(path)
                if self.__found_server_cb:
                    self.__found_server_cb(path)
            finally:
                pass

    def lost_server(self, path):
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

        self.__manager.connect_to_signal("FoundServer", self.found_server)
        self.__manager.connect_to_signal("LostServer", self.lost_server)
        self.__init_servers()

    def set_lost_server_cb(self, callback):
        self.__lost_server_cb = callback

    def set_found_server_cb(self, callback):
        self.__found_server_cb = callback

    def get_server_list(self):
        return self.__servers

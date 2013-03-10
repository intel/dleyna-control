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
from gi.repository import Gtk

from msd_generic_model import *
from msd_sort_order import *
from msd_upnp import *

class BrowseModel(GenericModel):
    def __init__(self, root, sort_order):
        super(BrowseModel, self).__init__()

        self.__sort_order = sort_order
        self.__root = root

        try:
            # if this container is in a container, add ".." row
            parent = root.get_prop('Parent')
            if (parent != root.get_prop('Path')):
                self._set_static_row(["..",
                                     None,
                                     None,
                                     "Container",
                                     parent,
                                     None,
                                     False])
        except:
            pass

        try:
            self.__child_count = self.__root.get_prop("ChildCount")
        except:
            pass

        self.set_request_range (0, GenericModel.max_items_per_fetch - 1)

    def __on_browse_reply (self, result):
        self._on_reply(result, self.__child_count)

    def _fetch_items(self, start, count):
        sort_descriptor = self.__sort_order.get_upnp_sort_order()
        self.__root.list_children(start, count,
                                  GenericModel.filter,
                                  sort_descriptor,
                                  self.__on_browse_reply, self._on_error)

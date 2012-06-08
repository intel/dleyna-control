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

import pygtk
pygtk.require('2.0')
import gtk
import dateutil.parser
import datetime

from msd_sort_order import *
from msd_upnp import *

class TreeNode(object):

    filter = ["Artist", "DisplayName", "URLs", "Date", "Path",
              "Type"]
    buffer_size = 50

    def __init__(self, props, parent, sort_order):
        self.__props = props
        self.__container = None
        self.__max_items = 0
        self.__parent = parent
        self.__sort_order = sort_order
        if self.is_container():
            self.__container = Container(props["Path"])
            try:
                self.__max_items = self.__container.get_prop("ChildCount")
            except Exception:
                pass
        self.__children = [None] * self.__max_items

    def is_container(self):
        return self.__props["Type"] == "container"

    def reset_children(self):
        self.__children = [None] * self.__max_items

    def get_num_children(self):
        return self.__max_items

    def get_props(self):
        return self.__props

    def get_parent(self):
        return self.__parent

    def flush(self):
        self.__flush_down()
        if self.__parent:
            self.__parent.__flush_up(self)

    def __flush_down(self):
        i = 0;
        while i < self.__max_items:
            if self.__children[i]:
                self.__children[i].__flush_down()
                self.__children[i] = None
            i = i + 1

    def __flush_up(self, child):
        i = 0;
        while i < self.__max_items:
            if self.__children[i]:
                if child != self.__children[i]:
                    self.__children[i].__flush_down()
                self.__children[i] = None
            i = i + 1
        if self.__parent:
            self.__parent.__flush_up(self)

    def get_child(self, child):
        retval = None
        if child < self.__max_items:
            retval = self.__children[child]
            if not retval:
                i = child + 1
                while (i < self.__max_items and (i - child) <
                       TreeNode.buffer_size and not self.__children[i]):
                    i = i + 1
                try:
                    sort_descriptor = self.__sort_order.get_upnp_sort_order()
                    try:
                        result = self.__container.list_children(child,
                                                                i - child,
                                                                TreeNode.filter,
                                                                sort_descriptor)
                    except Exception:
                        result = self.__container.list_children(child,
                                                                i - child,
                                                                TreeNode.filter)
                    i = child
                    for props in result:
                        self.__children[i] = TreeNode(props, self,
                                                      self.__sort_order)
                        i = i + 1
                    retval = self.__children[child]
                except Exception:
                    pass

        return retval

class BrowseModel(gtk.GenericTreeModel):
    columns = (("DisplayName", str), ("Artist", str), ("Date", str),
               ("Type",str), ("Path", str), ("URLs", str))

    def __init__(self, root):
        gtk.GenericTreeModel.__init__(self)

        self.__root = root

    def flush(self):
        self.__root.flush()

    def on_get_flags(self):
        return gtk.TREE_MODEL_LIST_ONLY | gtk.TREE_MODEL_ITERS_PERSIST

    def on_get_n_columns(self):
        return len(BrowseModel.columns)

    def on_get_column_type(self, n):
        return BrowseModel.columns[n][1]

    def __get_num_of_children(self):
        num = self.__root.get_num_children()
        if self.__root.get_parent():
            num = num + 1
        return num

    def on_get_iter(self, path):
        if path[0] >= self.__get_num_of_children():
            raise ValueError("Invalid Path")
        return path[0]

    def on_get_path(self, rowref):
        return (rowref,)

    def adjusted_on_get_value(self, rowref, col):
        retval = None
        key = BrowseModel.columns[col][0]
        node = self.__root.get_child(rowref)
        props = node.get_props()
        if key in props:
            data = props[key]
            if node.is_container():
                if col == 0:
                    retval = data
            else:
                if col == 2:
                    date = dateutil.parser.parse(data)
                    retval = date.strftime("%x")
                elif col == 3:
                    data = data[0].upper() + data[1:]
                    period = data.find('.')
                    if period >=0:
                        retval = data[:period]
                    else:
                        retval = data
                elif col == 5:
                    retval = data[0]
                else:
                    retval = data
        elif not node.is_container():
            if col == 1:
                retval = "Unknown"
            elif col == 2:
                retval = datetime.date.today().strftime("%x")
            else:
                retval = ""

        return retval

    def on_get_value(self, rowref, col):
        if self.__root.get_parent():
            if rowref == 0:
                if col == 0:
                    retval = ".."
                else:
                    retval = ""
            else:
                retval = self.adjusted_on_get_value(rowref - 1, col)
        else:
            retval = self.adjusted_on_get_value(rowref, col)

        return retval

    def on_iter_next(self, rowref):
        retval = None
        rowref = rowref + 1
        if rowref < self.__get_num_of_children():
            retval =  rowref

        return retval

    def on_iter_children(self, rowref):
        retval = 0
        if rowref:
            retval =  None
        return retval

    def on_iter_has_child(self, rowref):
        return False

    def on_iter_n_children(self, rowref):
        retval = 0
        if not rowref:
            retval = self.__get_num_of_children()
        return retval

    def on_iter_nth_child(self, rowref, child):
        retval = None
        if not rowref and child < self.__get_num_of_children():
            retval = child
        return retval

    def on_iter_parent(self, rowref):
        return None

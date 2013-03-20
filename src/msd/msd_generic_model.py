# dleyna-control
#
# Copyright (C) 2012-2013 Intel Corporation. All rights reserved.
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

# This is a base class for SearchModel and BrowseModel:
# They need to implement:
#     def _fetch_items(self, start, count)
# which needs to make sure _on_reply() or _on_error() is called.

import sys
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import GLib, GObject, Gtk
import dateutil.parser

from msd_upnp import *


# Use a dictionary to store results so we only end up using memory for 
# cached items. Class will call on_inserted/on_changed/on_deleted
# as needed.
# Note that this 'sparse dict' implementation is not 100% complete: e.g.
# "for x in results_dict" does not return the 'empty' rows.
class _ResultArray(dict):
    def __init__(self, empty_value, length=0,
                 on_inserted=None, on_changed=None, on_deleted=None):
        dict.__init__(self)
        self.__empty_value = empty_value
        self.__length = length
        self.__on_inserted = on_inserted
        self.__on_changed = on_changed
        self.__on_deleted = on_deleted

    def __len__(self):
        return self.__length

    def __contains__(self, key):
        return key < self.__length

    def __setitem__(self, key, value):
        new = False
        if (key >= self.__length):
            self.__length = key + 1
            new = True
        dict.__setitem__ (self, key, value)
        if (new):
            self.__on_inserted(key)
        else:
            self.__on_changed(key)

    def __getitem__(self, key):
        try:
            return dict.__getitem__(self, key)
        except KeyError:
            if (key >= 0 and key < self.__length):
                return self.__empty_value
            raise

    def set_length(self, length):
        if length > self.__length:
            for key in xrange(self.__length, length):
                self.__length = key + 1
                self.__on_inserted(key)
        elif length < self.__length:
            for key in xrange(self.__length - 1, length - 1, -1):
                try:
                    del self[key]
                except:
                    pass
                self.__length = key
                self.__on_deleted(key)

    def get_cached_item_count(self):
        return dict.__len__(self)


class GenericModel(GObject.GObject, Gtk.TreeModel):
    # columns
    COL_DISPLAY_NAME = 0
    COL_ARTIST = 1
    COL_DATE = 2
    COL_TYPE = 3
    COL_PATH = 4
    COL_URL = 5
    COL_LOADED = 6
    column_types = [str, str, str, str, str, str, bool]

    filter = ["Artist", "DisplayName", "URLs", "Date", "Path", "Type"]

    # maximum number of items to fetch at a time
    max_items_per_fetch = 50

    # Minimum number of items to query if server does not
    # tell us how many results there are
    min_items_default = 100

    @staticmethod
    def __create_row(item):
        try:
            date = dateutil.parser.parse(item['Date']).strftime("%x")
        except:
            date = None
        media_type = item.get('Type', '').capitalize().split('.', 1)[0]
        return [item.get('DisplayName', None),
                item.get('Artist', None),
                date,
                media_type,
                item.get('Path', None),
                item.get('URLs', [None])[0],
                True]

    def _set_static_row(self, item):
        if(len(self.__items)) > 0:
            # Not handling situations where the model is populated already
            raise IndexError
        self.__items[0] = item
        self.__static_items = 1

    def _on_reply(self, items, max_items):
        n_items = len(items)
        if max_items > 0:
            self.__length_is_known = True

        # 'add' empty rows before actual results
        index = (self.__request_start +
                 self.__result_count +
                 self.__static_items)
        if index > len(self.__items):
            self.__items.set_length(index)
        # add actual fetched results
        for item in items:
            self.__items[index] = self.__create_row (item)
            index = index + 1

        # 'add' (or remove) empty rows after actual results
        if max_items != 0:
            self.__items.set_length(max_items + self.__static_items)

        self.__result_count = self.__result_count + n_items
        print ("%d rows fetched (%d/%d rows cached)"
               % (n_items,
                  self.__items.get_cached_item_count(),
                  len(self.__items)))

        # Was a new request made while this one was executed?
        if (self.__restart_count > 0):
            self.__start_fetch (self.__restart_start, self.__restart_count)
            return

        # should we stop fetching now?
        if (n_items == 0 or
            self.__result_count >= self.__request_count or
            (max_items > 0 and self.__result_count >= max_items)):

            self.__fetch_in_progress = False
            if n_items == 0:
                self.__length_is_known = True
            return

        self.__do_fetch ()

    def _on_error(self, error):
        self.__fetch_in_progress = False
        print "Fetch failed: %s" % error

    def _fetch_items(self, start, count):
        raise NotImplementedError

    def __do_fetch (self):
        start = self.__request_start + self.__result_count
        count = min(self.__request_count - self.__result_count,
                    GenericModel.max_items_per_fetch)
        # call virtual function, implemented by subclasses 
        self._fetch_items(start, count)

    def __start_fetch(self, start, count):
        self.__fetch_in_progress = True
        self.__length_is_known = False
        self.__result_count = 0
        self.__restart_start = 0
        self.__restart_count = 0
        self.__request_start = start
        self.__request_count = count
        self.__do_fetch()

    def length_is_known(self):
        return self.__length_is_known

    def __on_inserted (self, row):
        path = Gtk.TreePath((row,))
        self.row_inserted (path, self.get_iter (path))

    def __on_changed (self, row):
        path = Gtk.TreePath((row,))
        self.row_changed (path, self.get_iter (path))

    def __on_deleted (self, row):
        self.row_deleted (Gtk.TreePath((row,)))

    def __init__(self):
        GObject.GObject.__init__(self)

        self.__stamp = GLib.random_int_range(-2147483648, 2147483647)
        empty_array = ["Loading...",None, None, None, None, False]
        self.__items = _ResultArray(empty_array,
                                   on_inserted = self.__on_inserted,
                                   on_changed = self.__on_changed,
                                   on_deleted = self.__on_deleted)
        self.__fetch_in_progress = False
        self.__length_is_known = False
        self.__static_items = 0
        self.__request_range = [-1, -1]

    def get_request_range (self):
        return self.__request_range

    def set_request_range (self, start, end):
        if (start >= self.__request_range[0] and
            end <= self.__request_range[1]):
            return

        self.__request_range = [start, end]

        # skip any rows in beginning or end that are already loaded
        try:
            while self.__items[start + self.__static_items][self.COL_LOADED] and start <= end:
                start = start + 1
            while self.__items[end + self.__static_items][self.COL_LOADED] and start <= end:
                end = end - 1
        except:
            pass

        if start > end:
            return

        if (self.__fetch_in_progress):
            self.__restart_count = end - start + 1
            self.__restart_start = start
        else:
            self.__start_fetch (start, end - start + 1)

    def flush(self):
        self.__request_range = [-1, -1]
        self.__items.set_length(0 + self.__static_items)
        self.set_request_range(0, GenericModel.max_items_per_fetch - 1)

    def do_get_flags(self):
        return Gtk.TreeModelFlags.LIST_ONLY

    def do_get_n_columns(self):
        return len(self.column_types)

    def do_get_column_type(self, n):
        return self.column_types[n]

    def do_get_iter(self, path):
        # return iterator for use in other do_* methods.
        # user_data is the index of the refered row.
        if len(self.__items) > 0 and path[0] < len(self.__items):
            tree_iter = Gtk.TreeIter()
            tree_iter.stamp = self.__stamp
            tree_iter.user_data = path[0]
            return (True, tree_iter)
        else:
            return (False, None)

    def do_get_path(self, tree_iter):
        if tree_iter.user_data is None:
            return Gtk.TreePath((None,))
        return Gtk.TreePath((tree_iter.user_data,))

    def do_get_value(self, tree_iter, col):
        try:
            if (col == self.COL_LOADED):
                return bool(self.__items[tree_iter.user_data][col])
            elif self.__items[tree_iter.user_data][col] == None:
                return ""
            else:
                return self.__items[tree_iter.user_data][col].encode('utf-8')
        except KeyError:
            return None

    def do_iter_next(self, tree_iter):
        length = len(self.__items)
        if tree_iter.user_data is None and length > 0:
            # return iter to first row
            tree_iter.user_data = 0
            return (True, tree_iter)
        elif tree_iter.user_data < length - 1:
            # return iter to next row
            tree_iter.user_data += 1
            return (True, tree_iter)
        else:
            return (False, None)

    def do_iter_has_child(self, tree_iter):
        return False

    def do_iter_n_children(self, parent_iter):
        if parent_iter is None:
            # special case: return number of top level children
            return len(self.__items)
        return 0

    def do_iter_nth_child(self, parent_iter, n):
        if parent_iter != None or n >= len(self.__items):
            return (False, None)
        tree_iter = Gtk.TreeIter()
        tree_iter.stamp = self.__stamp
        tree_iter.user_data = n
        return (True, tree_iter)

    def do_iter_parent(self, child_iter):
        return (False, None)

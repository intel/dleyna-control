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
import cStringIO
import dateutil.parser
import datetime

from msd_sort_order import *
from msd_upnp import *


# Use a dictionary to store results so we only end up using memory for 
# cached items. Class will call on_inserted/on_changed/on_deleted
# as needed.
# Note that this 'sparse dict' implementation is not 100% complete: e.g.
# "for x in results_dict" does not return the 'empty' rows.
class SearchResultArray(dict):
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


class SearchModel(gtk.GenericTreeModel):
    columns = (("DisplayName", str), ("Artist", str), ("Date", str),
               ("Type",str), ("Path", str), ("URL", str),
               ("Loaded", bool))
    filter = ["Artist", "DisplayName", "URLs", "Date", "Path",
              "Type"]

    # maximum number of items to fetch at a time
    max_items_per_search = 50

    # Minimum number of items to query if server does not
    # tell us how many results there are
    min_items_default = 100

    @staticmethod
    def __create_query_string(query, images, videos, music):
        search_string = ''

        if images or videos or music:
            q_buffer = cStringIO.StringIO()
            try:
                if query != "":
                    q_buffer.write('(Artist contains "{0}"\
 or DisplayName contains "{0}")'.format(query))
                    q_buffer.write(' and ')
                q_buffer.write(' ( ')
                if images:
                    q_buffer.write('Type derivedfrom "image" ')
                if videos:
                    if images:
                        q_buffer.write(' or ')
                    q_buffer.write('Type derivedfrom "video" ')
                if music:
                    if images or videos:
                        q_buffer.write(' or ')
                    q_buffer.write('Type derivedfrom "audio" ')
                q_buffer.write(' ) and ( RefPath exists false )')

                search_string = q_buffer.getvalue()
            finally:
                q_buffer.close()

        return search_string


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

    def __on_search_reply(self, items, max_items):
        # if server does not tell how many results there are, set
        # a sensible minimum
        if (max_items == 0):
            self.__request_count = max(self.__request_count,
                                       self.min_items_default)

        # 'add' empty rows before actual results
        index = self.__request_start + self.__result_count
        if index > len(self.__items):
            self.__items.set_length(index)

        # add actual fetched results
        for item in items:
            self.__items[index] = self.__create_row (item)
            index = index + 1

        # 'add' (or remove) empty rows after actual results
        if max_items != 0:
            self.__items.set_length(max_items)

        self.__result_count = self.__result_count + len(items)
        print ("%d rows fetched (%d/%d rows cached)"
               % (len(items), self.__items.get_cached_item_count(), len(self.__items)))

        # Was a new search request made while this one was executed?
        if (self.__restart_count > 0):
            self.__start_search (self.__restart_start, self.__restart_count)
            return

        # should we stop searching now?
        if len(items) == 0 or self.__result_count >= self.__request_count:
            self.__search_in_progress = False
            if max_items == 0 and self.__result_count >= self.__request_count:
                print "max_items not known, may have more rows available..."
                self.__may_have_more_results = True
            return

        self.__get_search_items()


    def __on_search_error(self, error):
        self.__search_in_progress = False
        print "Search failed: %s" % error

    def __get_search_items(self):
        start = self.__request_start + self.__result_count
        count = min(self.__request_count - self.__result_count,
                    SearchModel.max_items_per_search)

        self.__root.search(self.__search_string,
                           start, count,
                           SearchModel.filter,
                           self.__sort_order.get_upnp_sort_order(),
                           self.__on_search_reply,
                           self.__on_search_error)

    def __start_search(self, start, count):
        self.__search_in_progress = True
        self.__may_have_more_results = False
        self.__result_count = 0
        self.__restart_start = 0
        self.__restart_count = 0
        self.__request_start = start
        self.__request_count = count
        self.__get_search_items()

    def get_request_range (self):
        return self.__request_range

    def set_request_range (self, start, end):
        self.__request_range = [start, end]
        # skip any rows in beginning or end that are already loaded
        try:
            while self.__items[start][6] and start <= end:
                start = start + 1
            while self.__items[end][6] and start <= end:
                end = end - 1
        except:
            pass

        if start > end:
            return

        if (self.__search_in_progress):
            self.__restart_count = end - start + 1
            self.__restart_start = start
        else:
            self.__start_search (start, end - start + 1)

    def __on_inserted (self, row):
        path = (row,)
        self.row_inserted (path, self.get_iter (path))

    def __on_changed (self, row):
        path = (row,)
        self.row_changed (path, self.get_iter (path))

    def __on_deleted (self, row):
        self.row_deleted ((row,))

    def __init__(self, root, query, images, videos, music, sort_order):
        gtk.GenericTreeModel.__init__(self)
        empty_array = ["Loading...",None, None, None, None, False]
        self.__items = SearchResultArray(empty_array,
                                         on_inserted = self.__on_inserted,
                                         on_changed = self.__on_changed,
                                         on_deleted = self.__on_deleted)
        self.__root = root
        self.__sort_order = sort_order
        self.__search_in_progress = False
        self.__search_string = SearchModel.__create_query_string(query, images,
                                                                 videos, music)
        self.set_request_range (0, SearchModel.max_items_per_search - 1)

    def flush(self):
        self.__items.set_length (0)
        self.set_request_range (0, SearchModel.max_items_per_search - 1)

    def on_get_flags(self):
        return gtk.TREE_MODEL_LIST_ONLY

    def on_get_n_columns(self):
        return len(SearchModel.columns)

    def on_get_column_type(self, n):
        return SearchModel.columns[n][1]

    def on_get_iter(self, path):
        # return internal row reference (key) for use in on_* methods
        retval = None
        if len(self.__items) > 0 and path[0] < len(self.__items):
            retval = path[0]
        return retval

    def on_get_path(self, rowref):
        return (rowref, )

    def on_get_value(self, rowref, col):
        try:
            return self.__items[rowref][col]
        except KeyError:
            return None

    def on_iter_next(self, rowref):
        retval = None
        if rowref + 1 < len(self.__items):
            retval = rowref + 1
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
            retval = len(self.__items)
        return retval

    def on_iter_nth_child(self, rowref, child):
        retval = None
        if not rowref and child < len(self.__items):
            retval = child
        return retval

    def on_iter_parent(self, child):
        return None

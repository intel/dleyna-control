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
import cStringIO
import dateutil.parser
import datetime

from msd_sort_order import *
from msd_upnp import *

class SearchModel(gtk.GenericTreeModel):
    columns = (("DisplayName", str), ("Artist", str), ("Date", str),
               ("Type",str), ("Path", str), ("URLs", str))
    filter = ["Artist", "DisplayName", "URLs", "Date", "Path",
              "Type"]

    buffer_size = 50

    @staticmethod
    def __create_query_string(query, images, videos, music):
        search_string = None

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
                q_buffer.write(' )')
                search_string = q_buffer.getvalue()
            finally:
                q_buffer.close()

        return search_string

    def __get_search_items(self, start, count):
        if self.__items:
            end = start
            while (end < start + SearchModel.buffer_size and
                   end < self.__max_items and not self.__items[end]):
                end = end + 1
        else:
            end = count

        if start < end:
            count = end - start
            try:
                sort_descriptor = self.__sort_order.get_upnp_sort_order()
                items, max_items = self.__root.search(self.__search_string,
                                                      start, count,
                                                      SearchModel.filter,
                                                      sort_descriptor)

                max_items = max(max_items, len(items))

                # TODO: I need to inform list view if max item has changed?

                if max_items != self.__max_items:
                    self.__max_items = max_items
                    self.__items = [None] * self.__max_items
                for item in items:
                    self.__items[start] = item
                    start = start + 1
            except Exception:
                pass

    def __init__(self, root, query, images, videos, music, sort_order):
        gtk.GenericTreeModel.__init__(self)

        self.__items = None
        self.__max_items = 0
        self.__root = root
        self.__sort_order = sort_order
        self.__search_string = SearchModel.__create_query_string(query, images,
                                                                 videos, music)
        if self.__search_string:
            self.__get_search_items(0, SearchModel.buffer_size)

    def flush(self):
        i = 0
        while i < self.__max_items:
            self.__items[i] = None
            i = i + 1

    def on_get_flags(self):
        return gtk.TREE_MODEL_LIST_ONLY | gtk.TREE_MODEL_ITERS_PERSIST

    def on_get_n_columns(self):
        return len(SearchModel.columns)

    def on_get_column_type(self, n):
        return SearchModel.columns[n][1]

    def on_get_iter(self, path):
        if path[0] >= self.__max_items:
            raise ValueError("Invalid Path")
        return path[0]

    def on_get_path(self, rowref):
        return (rowref, )

    def on_get_value(self, rowref, col):
        retval = None
        self.__get_search_items(rowref, SearchModel.buffer_size)
        if rowref < self.__max_items and self.__items and self.__items[rowref]:
            key = SearchModel.columns[col][0]
            if key in self.__items[rowref]:
                data = self.__items[rowref][key]
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
            elif col == 1:
                retval = "Unknown"
            elif col == 2:
                retval = datetime.date.today().strftime("%x")
            else:
                retval = ""
        else:
            retval = ""

        return retval

    def on_iter_next(self, rowref):
        retval = None
        rowref = rowref + 1
        if rowref < self.__max_items:
            retval = rowref
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
            retval = self.__max_items
        return retval

    def on_iter_nth_child(self, rowref, child):
        retval = None
        if not rowref and child < self.__max_items:
            retval = child
        return retval

    def on_iter_parent(self, child):
        return None

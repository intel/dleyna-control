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
# Jussi Kukkonen <jussi.kukkonen@intel.com>
#

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
import cStringIO

from msd_generic_model import *
from msd_sort_order import *

class SearchModel(GenericModel):
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
                q_buffer.write('( ')
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

    def _fetch_items(self, start, count):
        if len(self.__search_string) > 0:
            self.__root.search(self.__search_string,
                               start, count,
                               GenericModel.filter,
                               self.__sort_order.get_upnp_sort_order(),
                               self._on_reply, self._on_error)
        else:
            self._on_reply([], 0)

    def __init__(self, root, query, images, videos, music, sort_order):
        super(SearchModel, self).__init__()
        self.__root = root
        self.__sort_order = sort_order
        self.__search_string = SearchModel.__create_query_string(query, images,
                                                                 videos, music)
        self.set_request_range (0, GenericModel.max_items_per_fetch - 1)

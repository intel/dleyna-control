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

import pygtk
pygtk.require('2.0')
import gtk
import glib
import dbus
import dbus.service
import dbus.mainloop.glib
import os

from msd_utils import *
from msd_upnp import *
from msd_search import *
from msd_browse import *
from msd_player import *

class MainWindow(object):

    container_padding = 2

    def delete_event(self, widget, event, data=None):
        return False

    def destroy(self, widget, data=None):
        if self.__overlay:
            self.__overlay.cancel_playback()
        gtk.main_quit()

    def __append_server_list_row(self, list_store, key, value):
        name, image = value
        if image:
            image = image.get_pixbuf()
            image = image.scale_simple(32, 32, gtk.gdk.INTERP_BILINEAR)
        return list_store.append([image, name, key])

    def __create_server_list_store(self):
        list_store = gtk.ListStore(gtk.gdk.Pixbuf, str, str)
        for key, value in self.__state.get_server_list().iteritems():
            self.__append_server_list_row(list_store, key, value)
        return list_store

    def __change_server(self, page, sel):
        model, row = sel.get_selected()
        if row != None:
            path = model.get_value(row, 2)
            if page == 0:
                if self.__search_path != path:
                    search_model =  SearchModel(Container(path),
                                                self.__search_entry.get_text(),
                                                self.__images.get_active(),
                                                self.__videos.get_active(),
                                                self.__music.get_active(),
                                                self.__sort_order)
                    self.__search_view.set_model(search_model)
                    self.__search_path = path
            elif self.__browse_path != path:
                browse_model = BrowseModel(Container(path),
                                           self.__sort_order)
                self.__browse_view.set_model(browse_model)
                self.__browse_path = path

    def __server_selected(self, sel):
        page = self.__notebook.get_current_page()
        self.__change_server(page, sel)

    def __select_server(self, rowref):
        selection = self.__server_view.get_selection()
        if selection.count_selected_rows() == 0:
            liststore = self.__server_view.get_model()
            selection = self.__server_view.get_selection()
            selection.select_iter(rowref)
            self.__server_view.set_cursor(liststore.get_path(rowref))

    def __create_server_list(self, table):
        liststore = self.__create_server_list_store()
        treeview = gtk.TreeView(liststore)
        treeview.set_headers_visible(True)

        column = gtk.TreeViewColumn()
        column.set_title("Servers")
        renderer = gtk.CellRendererPixbuf()
        column.pack_start(renderer, expand=False)
        column.add_attribute(renderer, 'pixbuf', 0)
        renderer = gtk.CellRendererText()
        column.pack_start(renderer, expand=False)
        column.add_attribute(renderer, 'text', 1)
        treeview.append_column(column)

        treeview.set_headers_clickable(True)

        treeview.get_selection().connect("changed", self.__server_selected)

        scrollwin = gtk.ScrolledWindow()
        scrollwin.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC);
        scrollwin.add(treeview)
        table.attach(scrollwin, left_attach=0, right_attach=1,
                     top_attach=0, bottom_attach=1)
        self.__server_view = treeview;

    def __column_clicked(self, column, sort_by):
        self.__sort_order.set_sort_by(sort_by)
        tv = column.get_tree_view()
        model = tv.get_model()

        # remove the model first to avoid handling lots of useless signals
        tv.set_model(None)
        model.flush()
        tv.set_model(model)

    def __cell_data_func(self, column, cell, model, tree_iter):
        path = model.get_path (tree_iter)

        # This could be a lot smarter: should fetch data so that
        # there's always at least 1 visible_range preloaded:
        # that way e.g. pressing PgDn would not show "Loading"
        requested_range = model.get_request_range()
        if (path[0] >= requested_range[0] and
            path[0] <= requested_range[1]):
            return

        if self.__notebook.get_current_page() == 0:
            visible_range = self.__search_view.get_visible_range()
        else:
            visible_range = self.__browse_view.get_visible_range()

        if (visible_range):
            visible_count = visible_range[1][0] - visible_range[0][0]
            start = visible_range[0][0] - visible_count // 2
            end = visible_range[1][0] + visible_count // 2
            model.set_request_range(max(0, start), min(len(model) - 1, end))

    def __create_column(self, treeview, name, col, width, sort_by, cell_data_func=None):
        renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn(name, renderer)
        column.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
        column.set_fixed_width(width)
        column.add_attribute(renderer, 'text', col)
        column.connect("clicked", self.__column_clicked, sort_by)
        column.set_cell_data_func(renderer, cell_data_func);
        treeview.append_column(column)

    def __close_overlay(self):
        self.__window.remove(self.__overlay.get_container())
        self.__window.add(self.__main_view)
        self.__overlay = None

    def __content_clicked(self, treeview, path, col):
        model = treeview.get_model()
        rowref = model.get_iter(path)
        name = model.get_value(rowref, model.COL_DISPLAY_NAME)
        ctype = model.get_value(rowref, model.COL_TYPE)
        path = model.get_value(rowref, model.COL_PATH)
        url = model.get_value(rowref, model.COL_URL)

        if (ctype == "Container"):
            if self.__notebook.get_current_page() == 1:
                browse_model = BrowseModel(Container(path),
                                           self.__sort_order)
                self.__browse_path = path
                self.__browse_view.set_model(browse_model)
        elif url != "":
            if ctype == "Image":
                self.__window.remove(self.__main_view)
                self.__overlay = PlayWindowImage(name, url,
                                                 self.__close_overlay)
                self.__window.add(self.__overlay.get_container())
            elif ctype == "Video":
                self.__window.remove(self.__main_view)
                self.__overlay = PlayWindowVideo(name, url,
                                                 self.__close_overlay)
                self.__window.add(self.__overlay.get_container())
            elif ctype == "Audio":
                try:
                    album_art_url = MediaObject(path).get_prop("AlbumArtURL")
                except Exception:
                    album_art_url = None
                self.__window.remove(self.__main_view)
                self.__overlay = PlayWindowAudio(name, url, album_art_url,
                                                 self.__close_overlay)
                self.__window.add(self.__overlay.get_container())

    def __create_common_list(self, store):
        treeview = gtk.TreeView(store)
        treeview.set_headers_visible(True)
        treeview.set_fixed_height_mode(True)

        self.__create_column(treeview, "Title", 0, 300, "DisplayName", self.__cell_data_func)
        self.__create_column(treeview, "Date", 2, 100, "Date")
        self.__create_column(treeview, "Type", 3, 75, "Type")
        self.__create_column(treeview, "Author", 1, 100, "Artist")

        treeview.set_headers_clickable(True)
        treeview.set_rules_hint(True)

        scrollwin = gtk.ScrolledWindow()
        scrollwin.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC);
        scrollwin.add(treeview)
        return (scrollwin, treeview)

    def __create_browse_view(self, notebook):
        tree_store = gtk.TreeStore(str, str, str, str)
        scrollwin, treeview = self.__create_common_list(tree_store)
        treeview.connect("row-activated", self.__content_clicked)
        self.__browse_view = treeview;
        notebook.append_page(scrollwin, gtk.Label("Browse"))

    def __create_search_list(self, container):
        list_store = gtk.ListStore(str, str, str, str)
        scrollwin, treeview = self.__create_common_list(list_store)
        container.pack_start(scrollwin, True, True, 0)
        treeview.connect("row-activated", self.__content_clicked)
        self.__search_view = treeview;

    def __search_criteria_changed(self, obj):
        self.__search_path = None
        self.__server_selected(self.__server_view.get_selection())

    def __create_check_box(self, title, container):
        cb = gtk.CheckButton(title)
        cb.set_active(True)
        cb.connect("toggled", self.__search_criteria_changed)
        container.pack_start(cb, True, True, MainWindow.container_padding)
        return cb

    def __create_search_controls(self, container):
        label = gtk.Label("Search: ")
        self.__search_entry = gtk.Entry()
        self.__search_entry.set_text("")
        self.__search_entry.connect("activate", self.__search_criteria_changed)
        container.pack_start(label, True, True, MainWindow.container_padding)
        container.pack_start(self.__search_entry, True, True,
                              MainWindow.container_padding)
        self.__music = self.__create_check_box("Music", container)
        self.__images = self.__create_check_box("Images", container)
        self.__videos = self.__create_check_box("Video", container)

    def __create_search_view(self, notebook):
        vbox = gtk.VBox(False, 0)
        hbox = gtk.HBox(True, 0)
        self.__create_search_list(vbox)
        self.__create_search_controls(hbox)
        vbox.pack_start(hbox, False, True, MainWindow.container_padding)
        notebook.append_page(vbox, gtk.Label("Search"))

    def __page_changed(self, notebook, page, page_number):
        sel = self.__server_view.get_selection()
        if sel:
            self.__change_server(page_number, sel)

    def __create_notebook(self, table):
        notebook = gtk.Notebook()
        self.__create_search_view(notebook)
        self.__create_browse_view(notebook)
        notebook.connect("switch-page", self.__page_changed)
        table.attach(notebook, left_attach=1, right_attach=4,
                     top_attach=0, bottom_attach=1)
        self.__notebook = notebook

    def __create_widgets(self, window):
        table = gtk.Table(rows=1, columns=4, homogeneous=True)
        self.__create_server_list(table)
        self.__create_notebook(table)
        window.add(table)
        self.__main_view = table

    def __create_window(self):
        window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        window.set_title("Media Service Demo")
        window.set_resizable(True)
        window.set_default_size(640, 480)
        window.connect("delete_event", self.delete_event)
        window.connect("destroy", self.destroy)
        self.__create_widgets(window)
        window.show_all()
        self.__window = window

    def __found_server(self, path):
        liststore = self.__server_view.get_model()
        value = self.__state.get_server_list()[path]
        rowref = self.__append_server_list_row(liststore, path, value)
        self.__select_server(rowref)

    def __lost_server(self, path):
        liststore = self.__server_view.get_model()
        rowref = liststore.get_iter_first()
        while rowref and liststore.get_value(rowref, 2) != path:
            rowref = liststore.iter_next(rowref)
        if rowref:
            path_to_delete = liststore.get_path(rowref)
            selection = self.__server_view.get_selection()
            selected_path = liststore.get_path(selection.get_selected()[1])
            liststore.remove(rowref)
            if path_to_delete == selected_path:
                rowref = liststore.get_iter_first()
                if rowref:
                    selection.select_iter(rowref)
                    self.__server_view.set_cursor(liststore.get_path(rowref))

    def __init__(self, state):
        self.__search_path = None
        self.__browse_path = None
        self.__state = state
        self.__state.set_lost_server_cb(self.__lost_server)
        self.__state.set_found_server_cb(self.__found_server)
        self.__create_window()
        self.__overlay = None
        self.__sort_order = SortOrder()

        liststore = self.__server_view.get_model()
        rowref = liststore.get_iter_first()
        if rowref:
            self.__select_server(rowref)

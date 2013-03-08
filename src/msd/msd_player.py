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
import glib
import gtk
import pygst
pygst.require("0.10")
import gst
import datetime

from msd_utils import *

class PlayWindowBase(object):

    def __init__(self, name, url, close_window):
        self.__name = name
        self.__url  = url
        self.__close_window = close_window

        self.__container = gtk.VBox(False, 0)
        self.drawing_area = gtk.DrawingArea()
        self.private_area = gtk.VBox(True, 0)
        self.ok_button = gtk.Button("Close")
        self.ok_button.connect("clicked", self.quit)
        self.__container.pack_start(self.drawing_area, True, True, 0)
        self.__container.pack_start(self.private_area, False, False, 0)
        self.__container.pack_start(self.ok_button, False, False, 0)

    def quit(self, button):
        self.__close_window()

    def get_container(self):
        return self.__container

    def cancel_playback(self):
        pass

    def draw_image(self, image):
        x = 0
        y = 0
        gc = self.drawing_area.get_style().fg_gc[gtk.STATE_NORMAL]
        rect = self.drawing_area.get_allocation()
        width_scale = image.get_width() / float(rect.width)
        height_scale = image.get_height() / float(rect.height)
        if ((width_scale < 1.0 and height_scale < 1.0) or
            (width_scale >= 1.0 and height_scale >= 1.0)):
            if width_scale < height_scale:
                divisor = height_scale
                x = (rect.width - int(image.get_width() / divisor)) / 2
            else:
                divisor = width_scale
                y = (rect.height - int(image.get_height() / divisor)) / 2
        elif width_scale > 1.0:
            divisor = width_scale
            y = (rect.height - int(image.get_height() / divisor)) / 2
        else:
            divisor = height_scale
            x = (rect.width - int(image.get_width() / divisor)) / 2

        scaled_image = image.scale_simple(int(image.get_width() / divisor),
                                          int(image.get_height() / divisor),
                                          gtk.gdk.INTERP_BILINEAR)
        self.drawing_area.window.draw_pixbuf(gc, scaled_image, 0, 0, x,
                                             y, -1, -1)


class PlayWindowImage(PlayWindowBase):

    def __on_pixbuf_loaded(self, pixbuf, userdata):
        self.__pixbuf = pixbuf
        self.draw_image (self.__pixbuf)

    def __init__(self, name, url, close_window):
        PlayWindowBase.__init__(self, name, url, close_window)
        try:
            PixbufAsyncLoader(url, self.__on_pixbuf_loaded)
            self.__pixbuf = None
            self.drawing_area.connect("expose-event", self.__draw)
        except Exception:
            pass

        self.get_container().show_all()

    def __draw(self, area, event):
        if self.__pixbuf:
            self.draw_image(self.__pixbuf)
        return True

class GStreamerWindow(PlayWindowBase):

    def __init__(self, name, url, close_window):
        PlayWindowBase.__init__(self, name, url, close_window)

        self.player = gst.element_factory_make("playbin2", "player")
        gsbus = self.player.get_bus()
        gsbus.add_signal_watch()
        gsbus.connect("message", self.gs_message_cb)

        self.player.set_property("uri", url)

        button_bar = gtk.HBox(False, 6)

        align = gtk.Alignment(0.5, 0.5, 0.0, 0.0)
        button_bar.pack_start(align, False, False, 0)

        self.__play_pause_button = gtk.Button()
        self.__play_pause_button.connect("clicked", self.__play_pause)
        self.__play_pause_image = gtk.Image()
        self.__play_pause_image.set_from_stock(gtk.STOCK_MEDIA_PAUSE,
                                               gtk.ICON_SIZE_BUTTON)
        self.__play_pause_button.add(self.__play_pause_image)
        align.add(self.__play_pause_button)

        self.__scale = gtk.HScale()
        self.__adjustment = gtk.Adjustment(0, 0, 0,
                                           1.0, 30.0, 1.0)
        self.__adjustment.connect("value-changed", self.__adjusted)
        self.__scale.set_adjustment(self.__adjustment)
        self.__scale.connect("format-value", self.__format_time)
        button_bar.pack_end(self.__scale, True, True, 0)

        self.private_area.pack_start(button_bar, False, False, 0)

        self.get_container().show_all()
        self.__update_pos_id = 0
        self.__state = gst.STATE_NULL
        self.player.set_state(gst.STATE_PLAYING)

    def __play_pause(self, button):
        if (self.__state == gst.STATE_PLAYING):
            self.player.set_state(gst.STATE_PAUSED)
        else:
            self.player.set_state(gst.STATE_PLAYING)

    def __update_pos(self, user_data=None):
        try:
            pos = self.player.query_position(gst.FORMAT_TIME, None)[0]
            if pos != -1:
                pos = pos / 1000000000.0
                self.__adjustment.handler_block_by_func(self.__adjusted)
                self.__adjustment.set_value(pos)
                self.__adjustment.handler_unblock_by_func(self.__adjusted)
        except Exception:
            pass
        return True

    def cancel_playback(self):
        self.player.set_state(gst.STATE_NULL)

    def quit(self, button):
        self.player.set_state(gst.STATE_NULL)
        PlayWindowBase.quit(self, button)

    def __seek (self, position):
        self.player.seek(1.0, gst.FORMAT_TIME, gst.SEEK_FLAG_FLUSH,
                         gst.SEEK_TYPE_SET, position,
                         gst.SEEK_TYPE_NONE, -1.0)

    def __adjusted(self, adjustment):
        self.__seek(adjustment.get_value() * 1000000000.0)

    def __format_time(self, scale, value):
        pos = int(self.__adjustment.get_value())
        return str(datetime.timedelta(seconds=pos))

    def __update_ui(self, state):
        if self.__state == state:
            return
        self.__state = state

        if (self.__state > gst.STATE_NULL and
            self.__adjustment.get_upper() == 0.0):
           try:
               duration = self.player.query_duration(gst.FORMAT_TIME, None)
               if duration[0] != -1:
                   self.__adjustment.set_upper(duration[0] / 1000000000)
           except Exception:
               pass

        if self.__state == gst.STATE_PLAYING:
            self.__play_pause_image.set_from_stock(gtk.STOCK_MEDIA_PAUSE,
                                                   gtk.ICON_SIZE_BUTTON)
            if self.__update_pos_id == 0:
                self.__update_pos_id = glib.timeout_add(500,
                                                        self.__update_pos,
                                                        None)
        else:
            self.__play_pause_image.set_from_stock(gtk.STOCK_MEDIA_PLAY,
                                                   gtk.ICON_SIZE_BUTTON)
            if self.__update_pos_id != 0:
                glib.source_remove(self.__update_pos_id)
                self.__update_pos_id = 0

    def gs_message_cb(self, bus, message):
        if message.type == gst.MESSAGE_EOS or message.type == gst.MESSAGE_ERROR:
            self.__seek(0)
            self.player.set_state(gst.STATE_PAUSED)
        elif message.type == gst.MESSAGE_STATE_CHANGED:
            (old, state, pending) =  message.parse_state_changed()
            self.__update_ui (state)
        elif message.type == gst.MESSAGE_ASYNC_DONE:
            self.__update_pos()

class PlayWindowAudio(GStreamerWindow):

    def __on_pixbuf_loaded(self, pixbuf, userdata):
        self.__pixbuf = pixbuf
        self.draw_image (self.__pixbuf)

    def __init__(self, name, url, album_art_url, close_window):
        GStreamerWindow.__init__(self, name, url, close_window)

        if album_art_url:
            try:
                PixbufAsyncLoader(url, self.__on_pixbuf_loaded)
                self.__pixbuf = None
                self.drawing_area.connect("expose-event", self.__draw)
            except Exception:
                pass

    def __draw(self, area, event):
        if self.__pixbuf:
            self.draw_image(self.__pixbuf)
        return True

class PlayWindowVideo(GStreamerWindow):

    def __init__(self, name, url, close_window):
        GStreamerWindow.__init__(self, name, url, close_window)

        gsbus = self.player.get_bus()
        gsbus.enable_sync_message_emission()
        gsbus.connect("sync-message::element", self.gs_sync_message_cb)


    def gs_sync_message_cb(self, bus, message):
        if message.structure != None and (message.structure.get_name() ==
                                          "prepare-xwindow-id"):
            message.src.set_property("force-aspect-ratio", True)
            gtk.gdk.threads_enter()
            message.src.set_xwindow_id(self.drawing_area.window.xid)
            gtk.gdk.threads_leave()

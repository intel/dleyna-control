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

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
gi.require_version('Gst', '1.0')
from gi.repository import GLib, Gtk, Gst, Gdk, GdkPixbuf

# For window.get_xid()
from gi.repository import GdkX11

# For xvimagesink.set_window_handle()
from gi.repository import GstVideo

import datetime

from msd_utils import *

class PlayWindowBase(object):

    def __init__(self, name, url, close_window):
        self.__name = name
        self.__url  = url
        self.__close_window = close_window

        self.__container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.drawing_area = Gtk.DrawingArea()
        self.private_area = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,
                                    homogeneous=True)
        self.ok_button = Gtk.Button("Close")
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

    def draw_image(self, image, context):
        x = 0
        y = 0
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
                                          GdkPixbuf.InterpType.BILINEAR)
        Gdk.cairo_set_source_pixbuf (context, scaled_image, x, y)
        context.paint()


class PlayWindowImage(PlayWindowBase):

    def __init__(self, name, url, close_window):
        PlayWindowBase.__init__(self, name, url, close_window)
        try:
            image = image_from_file(url)
            self.__image = image.get_pixbuf()
            self.drawing_area.connect("draw", self.__draw)
        except Exception:
            pass

        self.get_container().show_all()

    def __draw(self, widget, context):
        if self.__image:
            self.draw_image(self.__image, context)
        return True

class GStreamerWindow(PlayWindowBase):

    def __init__(self, name, url, close_window):
        PlayWindowBase.__init__(self, name, url, close_window)

        self.player = Gst.ElementFactory.make("playbin", "player")
        gsbus = self.player.get_bus()
        gsbus.add_signal_watch()
        gsbus.connect("message", self.gs_message_cb)

        self.player.set_property("uri", url)

        button_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,
                             spacing=6)
        align = Gtk.Alignment.new(0.5, 1.0, 0.0, 0.0)
        button_bar.pack_start(align, False, False, 0)

        self.__play_pause_button = Gtk.Button()
        self.__play_pause_button.connect("clicked", self.__play_pause)
        self.__play_pause_image = Gtk.Image()
        self.__play_pause_image.set_from_stock(Gtk.STOCK_MEDIA_PAUSE,
                                               Gtk.IconSize.BUTTON)
        self.__play_pause_button.add(self.__play_pause_image)
        align.add(self.__play_pause_button)

        self.__scale = Gtk.HScale()
        self.__adjustment = Gtk.Adjustment(0, 0, 0,
                                           1.0, 30.0, 1.0)
        self.__adjustment.connect("value-changed", self.__adjusted)
        self.__scale.set_adjustment(self.__adjustment)
        self.__scale.connect("format-value", self.__format_time)
        button_bar.pack_end(self.__scale, True, True, 0)

        self.private_area.pack_start(button_bar, False, False, 0)

        self.get_container().show_all()
        self.__update_pos_id = 0
        self.__state = Gst.State.NULL
        self.player.set_state(Gst.State.PLAYING)

    def __play_pause(self, button):
        if (self.__state == Gst.State.PLAYING):
            self.player.set_state(Gst.State.PAUSED)
        else:
            self.player.set_state(Gst.State.PLAYING)

    def __update_pos(self, user_data=None):
        success, pos = self.player.query_position(Gst.Format.TIME)
        if success:
            pos = pos / 1000000000.0
            self.__adjustment.handler_block_by_func(self.__adjusted)
            self.__adjustment.set_value(pos)
            self.__adjustment.handler_unblock_by_func(self.__adjusted)
        return True

    def cancel_playback(self):
        self.player.set_state(Gst.State.NULL)

    def quit(self, button):
        self.player.set_state(Gst.State.NULL)
        PlayWindowBase.quit(self, button)

    def __seek (self, position):
        self.player.seek(1.0, Gst.Format.TIME, Gst.SeekFlags.FLUSH,
                         Gst.SeekType.SET, position,
                         Gst.SeekType.NONE, -1.0)

    def __adjusted(self, adjustment):
        self.__seek(adjustment.get_value() * 1000000000.0)

    def __format_time(self, scale, value):
        pos = int(self.__adjustment.get_value())
        return str(datetime.timedelta(seconds=pos))

    def __update_ui(self, state):
        if self.__state == state:
            return
        self.__state = state

        if (self.__state > Gst.State.NULL and
            self.__adjustment.get_upper() == 0.0):
            success, duration = self.player.query_duration(Gst.Format.TIME)
            if success:
               self.__adjustment.set_upper(duration / 1000000000)

        if self.__state == Gst.State.PLAYING:
            self.__play_pause_image.set_from_stock(Gtk.STOCK_MEDIA_PAUSE,
                                                   Gtk.IconSize.BUTTON)
            if self.__update_pos_id == 0:
                self.__update_pos_id = GLib.timeout_add(500,
                                                        self.__update_pos,
                                                        None)
        else:
            self.__play_pause_image.set_from_stock(Gtk.STOCK_MEDIA_PLAY,
                                                   Gtk.IconSize.BUTTON)
            if self.__update_pos_id != 0:
                GLib.source_remove(self.__update_pos_id)
                self.__update_pos_id = 0

    def gs_message_cb(self, bus, message):
        if message.type == Gst.MessageType.EOS or message.type == Gst.MessageType.ERROR:
            self.__seek(0)
            self.player.set_state(Gst.State.PAUSED)
        elif message.type == Gst.MessageType.STATE_CHANGED:
            (old, state, pending) =  message.parse_state_changed()
            self.__update_ui (state)
        elif message.type == Gst.MessageType.ASYNC_DONE:
            self.__update_pos()

class PlayWindowAudio(GStreamerWindow):

    def __init__(self, name, url, album_art_url, close_window):
        GStreamerWindow.__init__(self, name, url, close_window)

        if album_art_url:
            try:
                image = image_from_file(album_art_url)
                self.__image = image.get_pixbuf()
                self.drawing_area.connect("draw", self.__draw)
            except Exception:
                pass

    def __draw(self, widget, context):
        if self.__image:
            self.draw_image(self.__image, context)
        return True

class PlayWindowVideo(GStreamerWindow):

    def __on_realize(self, widget):
        self.__xid = self.drawing_area.get_property('window').get_xid()

    def __init__(self, name, url, close_window):
        GStreamerWindow.__init__(self, name, url, close_window)

        # get window XID when widget is realized
        self.__xid = None
        self.drawing_area.connect ("realize", self.__on_realize)

        gsbus = self.player.get_bus()
        gsbus.enable_sync_message_emission()
        gsbus.connect("sync-message::element", self.gs_sync_message_cb)

    def gs_sync_message_cb(self, bus, message):
        if message.get_structure().get_name() == "prepare-window-handle":
            message.src.set_property("force-aspect-ratio", True)
            message.src.set_window_handle(self.__xid)

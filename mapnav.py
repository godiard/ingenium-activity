#!/usr/bin/env python
# Copyright (C) 2012, One Laptop Per Child
# Author, Gonzalo Odiard
# License: LGPLv2
#
# The class MapNavView draw a map from the top

import gtk
import gobject
import cairo
import logging

from game_map import GameMap
from mapview import TopMapView


class MapNavView(gtk.DrawingArea):

    __gsignals__ = {'position-changed': (gobject.SIGNAL_RUN_FIRST,
                          gobject.TYPE_NONE,
                          ([gobject.TYPE_INT, gobject.TYPE_INT,
                            gobject.TYPE_STRING]))}

    def __init__(self, game_map):
        self._game_map = game_map
        self.x = 0
        self.y = 0
        self.direction = 'S'
        self.cache_info = {}

        super(MapNavView, self).__init__()
        self.set_can_focus(True)
        self.add_events(gtk.gdk.KEY_PRESS_MASK)
        self.connect('expose_event', self.expose)
        self.connect('key-press-event', self._key_press_event_cb)

    def _key_press_event_cb(self, widget, event):
        keyname = gtk.gdk.keyval_name(event.keyval)
        if keyname not in ('Up', 'KP_Up', 'Down', 'KP_Down', 'Left', 'KP_Left',
                'Right', 'KP_Right'):
            return False

        x, y = self.x, self.y
        info_walls = self.get_information_walls(x, y, self.direction)

        new_x, new_y, new_direction = self.x, self.y, self.direction
        if keyname == 'Up' or keyname == 'KP_Up':
            new_x, new_y, new_direction = \
                    self._game_map.cross_door(x, y, self.direction)

        elif keyname == 'Down' or keyname == 'KP_Down':
            reversed_direction = \
                    self._game_map.get_reversed_direction(self.direction)
            wall_info = self._game_map.get_wall_info(x, y, reversed_direction)
            if wall_info is None or self._game_map.have_door(wall_info):
                new_x, new_y, new_direction = \
                        self._game_map.cross_door(x, y, reversed_direction)
                new_direction = self.direction
                if self._game_map.get_wall_info(new_x, new_y, new_direction) \
                        is None:
                    new_x, new_y, new_direction = \
                        self._game_map.go_forward(new_x, new_y, new_direction)

        elif keyname == 'Right' or keyname == 'KP_Right':
            new_x, new_y, new_direction = \
                    self._game_map.go_right(self.x, self.y, self.direction)

        elif keyname == 'Left' or keyname == 'KP_Left':
            new_x, new_y, new_direction = \
                    self._game_map.go_left(self.x, self.y, self.direction)
        if (new_x, new_y, new_direction) != (self.x, self.y, self.direction):
            self.x, self.y, self.direction = new_x, new_y, new_direction
            self.emit('position-changed', self.x, self.y, self.direction)
            self.queue_draw()
        return True

    def calculate_sizes(self, width, height):
        self._width = width
        self._height = height
        # used as unity 1/10 of the height
        self._grid_size = self._height / 12
        # the door is 3 units width and 6 units hight
        self._door_width = 3
        self._door_height = 6

    def expose(self, widget, event):
        rect = self.get_allocation()
        self.calculate_sizes(rect.width, rect.height)
        ctx = widget.window.cairo_create()
        # set a clip region for the expose event
        ctx.rectangle(event.area.x, event.area.y, event.area.width,
                event.area.height)
        ctx.clip()
        self.draw(ctx)
        return False

    def get_information_walls(self, x, y, direction):
        key = str(x) + direction + str(y)
        if key in self.cache_info:
            return self.cache_info[key]
        else:
            # have door?
            wall_info = self._game_map.get_wall_info(x, y, direction)
            have_door = self._game_map.have_door(wall_info)
            # there are a page at cw direction?
            cw_direction = self._game_map.get_direction_cw(direction)
            wall_cw = self._game_map.get_wall_info(x, y, cw_direction) is \
                    not None
            # there are a page at ccw direction?
            ccw_direction = self._game_map.get_direction_ccw(direction)
            wall_ccw = self._game_map.get_wall_info(x, y, ccw_direction) is \
                    not None
            # Wall color?
            wall_color = self._game_map.get_wall_color(x, y)
            info = {'have_door': have_door, 'wall_cw': wall_cw,
                    'wall_ccw': wall_ccw, 'wall_color': wall_color}
            self.cache_info[key] = info
            return info

    def draw(self, ctx):
        def darken(color, factor=0.8):
            return tuple(c * factor for c in color)

        x, y = self.x, self.y
        info_walls = self.get_information_walls(x, y, self.direction)
        # draw back wall
        ctx.rectangle(0, 0, self._width, self._height - self._grid_size)
        fill = info_walls['wall_color']
        stroke = (0, 0, 0)
        ctx.set_source_rgb(*fill)
        ctx.fill_preserve()
        ctx.set_source_rgb(*stroke)
        ctx.stroke()

        # draw floor

        ctx.rectangle(0, self._height - self._grid_size, self._width,
                self._grid_size)
        fill = (0, 0, 0)
        stroke = (1, 1, 1)
        ctx.set_source_rgb(*fill)
        ctx.fill_preserve()
        ctx.set_source_rgb(*stroke)
        ctx.stroke()

        if info_walls['have_door']:
            if self.direction in ('N', 'W'):
                # door is at rigth of the wall
                x = self._width - self._grid_size * (self._door_width + 2)
            else:
                x = self._grid_size * 2

            ctx.rectangle(x,
                    self._height - self._grid_size * (self._door_height + 1),
                    self._grid_size * self._door_width,
                    self._grid_size * self._door_height)
            fill = (0, 0, 0)
            stroke = (0, 0, 0)
            ctx.set_source_rgb(*fill)
            ctx.fill_preserve()
            ctx.set_source_rgb(*stroke)
            ctx.stroke()

        if info_walls['wall_cw']:
            ctx.move_to(self._width - self._grid_size, 0)
            ctx.line_to(self._width, 0)
            ctx.line_to(self._width, self._height)
            ctx.line_to(self._width - self._grid_size,
                    self._height - self._grid_size)
            ctx.close_path()
            fill = darken(info_walls['wall_color'])
            stroke = (0, 0, 0)
            ctx.set_source_rgb(*fill)
            ctx.fill_preserve()
            ctx.set_source_rgb(*stroke)
            ctx.stroke()

        if info_walls['wall_ccw']:
            ctx.move_to(0, 0)
            ctx.line_to(self._grid_size, 0)
            ctx.line_to(self._grid_size,
                    self._height - self._grid_size)
            ctx.line_to(0, self._height)
            ctx.close_path()
            fill = darken(info_walls['wall_color'])
            stroke = (0, 0, 0)
            ctx.set_source_rgb(*fill)
            ctx.fill_preserve()
            ctx.set_source_rgb(*stroke)
            ctx.stroke()


def show_position(nav_view, x, y, direction, top_view):
    top_view.show_position(x, y, direction)


def main():
    window = gtk.Window()
    game_map = GameMap()
    nav_view = MapNavView(game_map)
    top_view = TopMapView(game_map, 200, 200)
    top_view.show_position(nav_view.x, nav_view.y, nav_view.direction)
    nav_view.connect('position-changed', show_position, top_view)
    hbox = gtk.HBox()
    hbox.pack_start(nav_view, True, True)
    hbox.pack_start(top_view, False, False)
    window.add(hbox)
    nav_view.grab_focus()
    window.connect("destroy", gtk.main_quit)
    window.set_default_size(800, 600)
    window.show_all()
    gtk.main()

if __name__ == "__main__":
    main()

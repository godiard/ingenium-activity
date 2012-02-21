#!/usr/bin/env python
# Copyright (C) 2011, One Laptop Per Child
# Author, Gonzalo Odiard
# License: LGPLv2
#
# The class TopMapView draw a map from the top

import gtk
import cairo
from game_map import GameMap


class TopMapView(gtk.DrawingArea):

    def __init__(self, game_map, width, height):
        self._game_map = game_map
        self._width = width
        self._height = height
        self._show_position = None
        super(TopMapView, self).__init__()
        self.set_size_request(width, height)
        self.connect('expose_event', self.expose)

    def show_position(self, x, y, direction):
        self._show_position = {'x': x, 'y': y, 'direction': direction}
        self.queue_draw()

    def hide_position(self, x, y, direction):
        self._show_position = None
        self.queue_draw()

    def calculate_sizes(self, width, height):
        # calculate cell size
        cell_width = self._width / self._game_map.data['max_x']
        cell_height = self._height / self._game_map.data['max_y']
        self.cell_size = min(cell_width, cell_height)
        self._map_width = self.cell_size * self._game_map.data['max_x']
        self.margin_x = (width - self._map_width) / 2
        self._map_height = self.cell_size * self._game_map.data['max_y']
        self.margin_y = (height - self._map_height) / 2
        self._door_width = self.cell_size / 3

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

    def draw(self, ctx):
        # background
        ctx.rectangle(self.margin_x, self.margin_y, self._map_width,
                self._map_height)
        fill = (0, 0, 0)
        stroke = (1, 1, 1)

        ctx.set_source_rgb(*fill)
        ctx.fill_preserve()
        ctx.set_source_rgb(*stroke)
        ctx.stroke()

        # draw cells
        for x in range(self._game_map.data['max_x']):
            for y in range(self._game_map.data['max_y']):
                # Draw North
                direction = 'N'
                wall_info = self._game_map.get_wall_info(x, y, direction)
                x_pos = self.margin_x + x * self.cell_size
                y_pos = self.margin_y + y * self.cell_size
                if wall_info is not None:
                    if self._game_map.have_door(x, y, direction):
                        # draw door
                        ctx.move_to(x_pos, y_pos)
                        ctx.line_to(x_pos + self._door_width, y_pos)
                        ctx.stroke()
                        ctx.move_to(x_pos + self._door_width * 2, y_pos)
                        ctx.line_to(x_pos + self.cell_size, y_pos)
                    else:
                        ctx.move_to(x_pos, y_pos)
                        ctx.line_to(x_pos + self.cell_size, y_pos)
                    ctx.stroke()

                # Draw West
                direction = 'W'
                wall_info = self._game_map.get_wall_info(x, y, direction)
                if wall_info is not None:
                    if self._game_map.have_door(x, y, direction):
                        # draw door
                        ctx.move_to(x_pos, y_pos)
                        ctx.line_to(x_pos, y_pos + self._door_width)
                        ctx.stroke()
                        ctx.move_to(x_pos, y_pos + self._door_width * 2)
                        ctx.line_to(x_pos, y_pos + self.cell_size)
                    else:
                        ctx.move_to(x_pos, y_pos)
                        ctx.line_to(x_pos, y_pos + self.cell_size)
                        ctx.stroke()

        if self._show_position is not None:
            x = self._show_position['x']
            y = self._show_position['y']
            direction = self._show_position['direction']
            x_pos = self.margin_x + x * self.cell_size + self.cell_size / 2
            y_pos = self.margin_y + y * self.cell_size + self.cell_size / 2
            border = 3
            if direction == 'N':
                point2_x = self.margin_x + x * self.cell_size + border
                point2_y = self.margin_y + y * self.cell_size + border
                point3_x = self.margin_x + (x + 1) * self.cell_size - border
                point3_y = self.margin_y + y * self.cell_size + border
            elif direction == 'E':
                point2_x = self.margin_x + (x + 1) * self.cell_size - border
                point2_y = self.margin_y + y * self.cell_size + border
                point3_x = self.margin_x + (x + 1) * self.cell_size - border
                point3_y = self.margin_y + (y + 1) * self.cell_size - border
            elif direction == 'S':
                point2_x = self.margin_x + (x + 1) * self.cell_size - border
                point2_y = self.margin_y + (y + 1) * self.cell_size - border
                point3_x = self.margin_x + x * self.cell_size + border
                point3_y = self.margin_y + (y + 1) * self.cell_size - border
            elif direction == 'W':
                point2_x = self.margin_x + x * self.cell_size + border
                point2_y = self.margin_y + (y + 1) * self.cell_size - border
                point3_x = self.margin_x + x * self.cell_size + border
                point3_y = self.margin_y + y * self.cell_size + border

            ctx.move_to(x_pos, y_pos)
            ctx.line_to(point2_x, point2_y)
            ctx.line_to(point3_x, point3_y)
            ctx.close_path()
            fill = (1, 0, 0)
            ctx.set_source_rgb(*fill)
            ctx.fill()


def main():
    window = gtk.Window()
    game_map = GameMap()
    map_view = TopMapView(game_map, 200, 200)

    window.add(map_view)
    window.connect("destroy", gtk.main_quit)
    window.show_all()
    gtk.main()

if __name__ == "__main__":
    main()

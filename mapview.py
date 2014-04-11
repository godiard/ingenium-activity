#!/usr/bin/env python
# Copyright (C) 2011, One Laptop Per Child
# Author, Gonzalo Odiard
# License: LGPLv2
#
# The class TopMapView draw a map from the top

from gi.repository import Gtk
import cairo
from game_map import GameMap

# view_data =  width, height, show_position


def draw(ctx, game_map, view_data):
    # calculate cell size
    cell_width = view_data['width'] / game_map.data['max_x']
    cell_height = view_data['height'] / game_map.data['max_y']
    cell_size = min(cell_width, cell_height)
    map_width = cell_size * game_map.data['max_x']
    margin_x = (view_data['width'] - map_width) / 2
    map_height = cell_size * game_map.data['max_y']
    margin_y = (view_data['height'] - map_height) / 2
    door_width = cell_size / 3

    if 'x' in view_data:
        margin_x = view_data['x']
    if 'y' in view_data:
        margin_y = view_data['y']

    # background
    ctx.rectangle(margin_x, margin_y, map_width, map_height)
    fill = (0, 0, 0)
    stroke = (1, 1, 1)

    ctx.set_source_rgb(*fill)
    ctx.fill_preserve()
    ctx.set_source_rgb(*stroke)
    ctx.stroke()

    # draw cells
    for x in range(game_map.data['max_x']):
        for y in range(game_map.data['max_y']):
            # Draw North
            direction = 'N'
            wall_info = game_map.get_wall_info(x, y, direction)
            x_pos = margin_x + x * cell_size
            y_pos = margin_y + y * cell_size
            if wall_info is not None:
                if game_map.have_door(x, y, direction):
                    # draw door
                    ctx.move_to(x_pos, y_pos)
                    ctx.line_to(x_pos + door_width, y_pos)
                    ctx.stroke()
                    ctx.move_to(x_pos + door_width * 2, y_pos)
                    ctx.line_to(x_pos + cell_size, y_pos)
                else:
                    ctx.move_to(x_pos, y_pos)
                    ctx.line_to(x_pos + cell_size, y_pos)
                ctx.stroke()

            # Draw West
            direction = 'W'
            wall_info = game_map.get_wall_info(x, y, direction)
            if wall_info is not None:
                if game_map.have_door(x, y, direction):
                    # draw door
                    ctx.move_to(x_pos, y_pos)
                    ctx.line_to(x_pos, y_pos + door_width)
                    ctx.stroke()
                    ctx.move_to(x_pos, y_pos + door_width * 2)
                    ctx.line_to(x_pos, y_pos + cell_size)
                else:
                    ctx.move_to(x_pos, y_pos)
                    ctx.line_to(x_pos, y_pos + cell_size)
                    ctx.stroke()

    if view_data['show_position'] is not None:
        x = view_data['show_position']['x']
        y = view_data['show_position']['y']
        direction = view_data['show_position']['direction']
        x_pos = margin_x + x * cell_size + cell_size / 2
        y_pos = margin_y + y * cell_size + cell_size / 2
        border = 3
        if direction == 'N':
            point2_x = margin_x + x * cell_size + border
            point2_y = margin_y + y * cell_size + border
            point3_x = margin_x + (x + 1) * cell_size - border
            point3_y = margin_y + y * cell_size + border
        elif direction == 'E':
            point2_x = margin_x + (x + 1) * cell_size - border
            point2_y = margin_y + y * cell_size + border
            point3_x = margin_x + (x + 1) * cell_size - border
            point3_y = margin_y + (y + 1) * cell_size - border
        elif direction == 'S':
            point2_x = margin_x + (x + 1) * cell_size - border
            point2_y = margin_y + (y + 1) * cell_size - border
            point3_x = margin_x + x * cell_size + border
            point3_y = margin_y + (y + 1) * cell_size - border
        elif direction == 'W':
            point2_x = margin_x + x * cell_size + border
            point2_y = margin_y + (y + 1) * cell_size - border
            point3_x = margin_x + x * cell_size + border
            point3_y = margin_y + y * cell_size + border

        ctx.move_to(x_pos, y_pos)
        ctx.line_to(point2_x, point2_y)
        ctx.line_to(point3_x, point3_y)
        ctx.close_path()
        fill = (1, 0, 0)
        ctx.set_source_rgb(*fill)
        ctx.fill()


class TopMapView(Gtk.DrawingArea):

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

    def expose(self, widget, event):
        rect = self.get_allocation()
        ctx = widget.window.cairo_create()
        ctx.save()
        # set a clip region for the expose event
        ctx.rectangle(event.area.x, event.area.y, event.area.width,
                event.area.height)
        ctx.clip()
        view_data = {'width': self._width, 'height': self._height,
                'show_position': self._show_position}

        draw(ctx, self._game_map, view_data)
        ctx.restore()
        return False


def main():
    window = Gtk.Window()
    game_map = GameMap()
    map_view = TopMapView(game_map, 200, 200)

    window.add(map_view)
    window.connect("destroy", Gtk.main_quit)
    window.show_all()
    Gtk.main()

if __name__ == "__main__":
    main()

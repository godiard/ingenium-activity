#!/usr/bin/env python
# Copyright (C) 2012, One Laptop Per Child
# Author, Gonzalo Odiard
# License: LGPLv2
#
# The class MapNavView draw a map from the top

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GdkPixbuf
from gi.repository import GObject
import logging
from gi.repository import Rsvg

from sugar3.graphics import style

from game_map import GameMap
from character import Character
from stateview import StateView
import mapview

WIDTH_CONTROL_LINES = 2
RESIZE_HANDLE_SIZE = 10

SELECTION_MODE_MOVE = 1
SELECTION_MODE_RESIZE = 2


class SelectedObject():

    def __init__(self):
        pass


class MapNavView(Gtk.DrawingArea):

    __gsignals__ = {'position-changed': (GObject.SignalFlags.RUN_FIRST,
                          None,
                          ([GObject.TYPE_INT, GObject.TYPE_INT,
                            GObject.TYPE_STRING])),
                    'map-updated': (GObject.SignalFlags.RUN_FIRST,
                          None,
                          ([GObject.TYPE_INT, GObject.TYPE_INT,
                            GObject.TYPE_STRING])),
                    'resource-clicked': (GObject.SignalFlags.RUN_FIRST,
                          None, ([GObject.TYPE_STRING])),
                    'question-clicked': (GObject.SignalFlags.RUN_FIRST,
                          None, ([GObject.TYPE_STRING]))}

    MODE_PLAY = 0
    MODE_EDIT = 1

    def __init__(self, game_map, model, mode=MODE_PLAY):
        self._game_map = game_map
        self._model = model
        self.x = 0
        self.y = 0
        self.direction = 'S'
        self.cache_info = {}
        self.view_mode = mode
        self.selected = None
        super(MapNavView, self).__init__()
        self.set_can_focus(True)
        self.add_events(Gdk.EventMask.KEY_PRESS_MASK | Gdk.EventMask.POINTER_MOTION_MASK |
                Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.BUTTON_RELEASE_MASK |
                Gdk.EventMask.BUTTON1_MOTION_MASK)
        self.connect('draw', self.__draw_cb)
        self.connect('key-press-event', self.__key_press_event_cb)
        self.connect('button_press_event', self.__button_press_event_cb)
        self.connect('motion_notify_event', self.__motion_notify_event_cb)
        self.connect('button_release_event', self.__button_release_event_cb)

        self._character = Character(self)
        self._is_walking = False

        def size_allocate_cb(widget, allocation):
            self.calculate_sizes(allocation.width, allocation.height)
            if self.view_mode == self.MODE_PLAY:
                character_y = allocation.height - self._grid_size
                self._character.pos = [style.GRID_CELL_SIZE, character_y]
                self._character.direction = 1
            self.disconnect(self._setup_handle)

        self._setup_handle = self.connect('size_allocate',
                                          size_allocate_cb)

        self._state_view = None
        if self.view_mode == self.MODE_PLAY:
            cell = style.GRID_CELL_SIZE / 2
            self._state_view = StateView(self._model, cell, cell, cell)

    def clear_cache(self):
        self.cache_info = {}

    def __key_press_event_cb(self, widget, event):
        keyname = Gdk.keyval_name(event.keyval)
        if keyname not in ('Up', 'KP_Up', 'Down', 'KP_Down', 'Left', 'KP_Left',
                'Right', 'KP_Right'):
            return False

        x, y = self.x, self.y
        #info_walls = self.get_information_walls(x, y, self.direction)

        new_x, new_y, new_direction = self.x, self.y, self.direction
        if keyname == 'Up' or keyname == 'KP_Up':
            new_x, new_y, new_direction = \
                    self._game_map.cross_door(x, y, self.direction)

        elif keyname == 'Down' or keyname == 'KP_Down':
            reversed_direction = \
                    self._game_map.get_reversed_direction(self.direction)
            wall_info = self._game_map.get_wall_info(x, y, reversed_direction)
            if wall_info is None or \
                    self._game_map.have_door(x, y, reversed_direction):
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

    def __button_press_event_cb(self, widget, event):
        info_walls = self.get_information_walls(self.x, self.y,
                self.direction)
        for wall_object in info_walls['objects']:
            wall_x, wall_y = wall_object['wall_x'], wall_object['wall_y']
            wall_x, wall_y = self.wall_to_view(wall_x, wall_y)
            width, height = wall_object['width'], wall_object['height']
            # check if is over the image
            if wall_x < event.x < wall_x + width and \
                wall_y < event.y < wall_y + height:
                if self.view_mode == self.MODE_EDIT:
                    # in edit mode prepare to move the object
                    self.selected = SelectedObject()
                    self.selected.data = wall_object
                    self.selected.dx = wall_x - event.x
                    self.selected.dy = wall_y - event.y
                    self.selected.mode = SELECTION_MODE_MOVE
                    self.update_wall_info(self.x, self.y, self.direction)
                else:
                    # in play mode trigger event
                    if 'type_object' in wall_object:
                        if wall_object['type_object'] == 'resource':
                            self.emit('resource-clicked',
                                    wall_object['id_object'])
                        if wall_object['type_object'] == 'question':
                            self.emit('question-clicked',
                                    wall_object['id_object'])

            if self.view_mode == self.MODE_EDIT:
                # check resize
                if wall_x - RESIZE_HANDLE_SIZE / 2 < event.x < \
                        wall_x + RESIZE_HANDLE_SIZE / 2 and \
                    wall_y - RESIZE_HANDLE_SIZE / 2 < event.y < \
                        wall_y + RESIZE_HANDLE_SIZE / 2:
                    if self.selected is None:
                        self.selected = SelectedObject()
                        self.selected.data = wall_object
                    self.selected.mode = SELECTION_MODE_RESIZE
                    self.selected.x = event.x
                    self.selected.y = event.y
                    self.update_wall_info(self.x, self.y, self.direction)

        if self.view_mode == self.MODE_PLAY and not self._is_walking:
            # verify doors
            if self._check_over_door(info_walls, event.x, event.y):
                logging.error('Door clicked')
                new_x, new_y, new_direction = self._game_map.cross_door(
                        self.x, self.y, self.direction)
                self._new_wall_char_position = int(event.x)
                self._move_character(event.x, new_x,
                        new_y, new_direction)
            # verify lateral walls
            elif self._check_left_wall(event.x):
                logging.error('Left wall clicked')
                new_x, new_y, new_direction = self._game_map.go_left(self.x,
                        self.y, self.direction)
                char_finish = 0
                if info_walls['wall_ccw']:
                    char_finish = self._grid_size - 1
                self._new_wall_char_position = self._width - self._grid_size \
                        - self._character.sprite.cel_width
                self._move_character(char_finish, new_x, new_y, new_direction)

            elif self._check_right_wall(event.x):
                logging.error('Right wall clicked')
                new_x, new_y, new_direction = self._game_map.go_right(self.x,
                        self.y, self.direction)
                char_width = self._character.sprite.cel_width
                char_finish = self._width - char_width + 1
                if info_walls['wall_cw']:
                    char_finish = char_finish - self._grid_size
                self._new_wall_char_position = self._grid_size
                self._move_character(char_finish, new_x, new_y, new_direction)
            else:
                self._move_character(event.x, self.x, self.y, self.direction)

    def _check_over_door(self, info_walls, x, y):
        # verify doors
        if info_walls['have_door'] != []:
            door_x = self._get_door_x()
            door_y = self._get_door_y()
            door_width = self._grid_size * self._door_width
            door_height = self._grid_size * self._door_height
            if door_x < x < door_x + door_width and \
                door_y < y < door_y + door_height:
                return True
        return False

    def _check_left_wall(self, x):
        return x < self._grid_size

    def _check_right_wall(self, x):
        return x > self._width - self._grid_size

    def _move_character(self, character_destination, new_map_x, new_map_y,
            new_map_direction):
        """
        Move the character to the next position,
        if needed, because the character is going to another wall or
        to a door, change the map view position
        """
        character_pos = self._character.pos[0]
        if character_destination < character_pos:
            self._character.direction = -1
        else:
            self._character.direction = 1
        self._character_destination = character_destination
        self._new_map_position = (new_map_x, new_map_y, new_map_direction)
        GObject.timeout_add(100, self._update_timer)

    def _update_timer(self):
        self._is_walking = True
        if self.is_drawable():
            rect = self._character.update()
            self.queue_draw_area(*rect)
        finish = abs(self._character_destination - self._character.pos[0]) < \
                self._character.speed
        if finish:
            self._is_walking = False
            if (self.x, self.y, self.direction) != self._new_map_position:
                self.x, self.y, self.direction = self._new_map_position
                self.emit('position-changed', self.x, self.y, self.direction)
                self._character.pos[0] = self._new_wall_char_position
                self.queue_draw()
        return not finish

    def __motion_notify_event_cb(self, widget, event):
        if self.view_mode == self.MODE_EDIT:
            if self.selected is not None:
                # move the object
                # TODO: control limits
                if self.selected.mode == SELECTION_MODE_MOVE:
                    x = event.x + self.selected.dx
                    y = event.y + self.selected.dy
                    wall_x, wall_y = self.view_to_wall(x, y)
                    self.selected.data['original']['wall_x'] = wall_x
                    self.selected.data['original']['wall_y'] = wall_y
                    self.update_wall_info(self.x, self.y, self.direction)
                elif self.selected.mode == SELECTION_MODE_RESIZE:
                    wall_scale = self.selected.data['original']['wall_scale']
                    if event.x > self.selected.x and event.y > self.selected.y:
                        if wall_scale >= 0.05:
                            self.selected.data['original']['wall_scale'] = \
                                wall_scale - 0.01
                    else:
                        self.selected.data['original']['wall_scale'] = \
                                wall_scale + 0.01
                    self.update_wall_info(self.x, self.y, self.direction)
        if self.view_mode == self.MODE_PLAY:
            info_walls = self.get_information_walls(self.x, self.y,
                    self.direction)
            if self._check_over_door(info_walls, event.x, event.y):
                self.get_window().set_cursor(Gdk.Cursor.new(Gdk.SB_UP_ARROW))
            # verify lateral walls
            elif self._check_left_wall(event.x):
                self.get_window().set_cursor(Gdk.Cursor.new(Gdk.SB_LEFT_ARROW))
            elif self._check_right_wall(event.x):
                self.get_window().set_cursor(Gdk.Cursor.new(Gdk.SB_RIGHT_ARROW))
            else:
                self.get_window().set_cursor(None)

    def __button_release_event_cb(self, widget, event):
        if self.selected is not None:
            self.selected.mode = None

    def remove_selected_object(self):
        if self.selected is not None:
            wall_object = self.selected.data['original']
            self._game_map.del_object_from_wall(self.x, self.y,
                    self.direction, wall_object)
            self.update_wall_info(self.x, self.y, self.direction)
            self.selected = None

    def view_to_wall(self, x, y):
        # receive int, int and return
        # float, float from 0 to 100 relative
        # to the height and width of the view
        # we save in the model this values and calculate again before display
        x2 = float(x) * 100.0 / float(self._width)
        y2 = float(y) * 100.0 / float(self._height)
        return x2, y2

    def wall_to_view(self, x, y):
        # receive float, float from 0 to 100 and return
        # int, int relative to the height and width of the view
        x2 = x * float(self._width) / 100.0
        y2 = y * float(self._height) / 100.0
        return int(x2), int(y2)

    def calculate_sizes(self, width, height):
        self._width = width
        self._height = height
        # used as unity 1/12 of the height
        self._grid_size = self._height / 12
        # the door is 3 units width and 6 units hight
        self._door_width = 3
        self._door_height = 6

    def __draw_cb(self, widget, ctx):
        rect = self.get_allocation()
        # set a clip region for the expose event
        #ctx.rectangle(event.area.x, event.area.y, event.area.width,
        #        event.area.height)
        #ctx.clip()
        #logging.error('expose clipping area %d %d %d %d', event.area.x,
        #        event.area.y, event.area.width, event.area.height)
        clip_x, clip_y, clip_width, clip_height = ctx.clip_extents()
        self.draw(ctx, clip_x, clip_y, clip_width, clip_height)

        if self.view_mode == self.MODE_PLAY:
            position = {'x': self.x, 'y': self.y, 'direction': self.direction}
            view_data = {'width': 150, 'height': 150,
                    'show_position': position, 'x': rect.width - 150, 'y': 30}
            mapview.draw(ctx, self._game_map, view_data)
            self._state_view.draw(ctx)
            self._character.draw(ctx)
        return False

    def receive_update_wall_info(self, mapnav, x, y, direction):
        self.update_wall_info(x, y, direction, redraw=False)

    def update_wall_info(self, x, y, direction, redraw=True):
        key = str(x) + direction + str(y)
        if key in self.cache_info:
            del self.cache_info[key]
        if self.view_mode == self.MODE_EDIT:
            self.emit('map-updated', self.x, self.y, self.direction)
        if redraw:
            self.queue_draw()

    def get_information_walls(self, x, y, direction):
        key = str(x) + direction + str(y)
        if key in self.cache_info:
            return self.cache_info[key]
        else:
            wall_objects = []
            objects = self._game_map.get_wall_info(x, y, direction)
            for wall_object in objects:
                image_file_name = wall_object['image_file_name']
                new_dict = {}
                new_dict.update(wall_object)
                new_dict['original'] = wall_object
                if image_file_name.endswith('.svg'):
                    # create a new dict to add the svg handle
                    # can't be in the model because can't be put in the json
                    if not 'svg_image_cache' in wall_object:
                        svg = Rsvg.Handle.new_from_file(image_file_name)
                        new_dict['svg_image_cache'] = svg
                else:
                    if not 'pxb_image_cache' in wall_object:
                        pxb = GdkPixbuf.Pixbuf.new_from_file(image_file_name)
                        new_dict['pxb_image_cache'] = pxb

                wall_objects.append(new_dict)

            # have door?
            have_door = self._game_map.have_door(x, y, direction)
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
                    'wall_ccw': wall_ccw, 'wall_color': wall_color,
                    'objects': wall_objects}
            self.cache_info[key] = info
            return info

    def draw(self, ctx, clip_x, clip_y, clip_width, clip_height):
        def darken(color, factor=0.8):
            return tuple(c * factor for c in color)
        ctx.save()
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

        if info_walls['have_door'] != []:
            x_door = self._get_door_x()
            self.draw_door(ctx, x_door, info_walls['have_door'])

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
        ctx.restore()
        if info_walls['objects']:
            for wall_object in info_walls['objects']:
                image_file_name = wall_object['image_file_name']
                wall_x, wall_y = wall_object['wall_x'], wall_object['wall_y']
                wall_x, wall_y = self.wall_to_view(wall_x, wall_y)
                wall_scale = wall_object['wall_scale']
                ctx.save()
                if image_file_name.endswith('.svg'):
                    svg = wall_object['svg_image_cache']
                    scale = float(self._height) * wall_scale / \
                            float(svg.props.height)
                    width = int(svg.props.width * scale)
                    height = int(svg.props.height * scale)

                    # verify if is out of the clip area
                    if wall_x + width < clip_x or \
                        wall_x > clip_x + clip_width or \
                        wall_y + height < clip_y or \
                        wall_y > clip_y + clip_height:
                        break
                    #logging.error('Drawing object %s at %d %d w %d h %d',
                    #        image_file_name, wall_x, wall_y, width, height)

                    ctx.translate(wall_x, wall_y)
                    ctx.scale(scale, scale)
                    svg.render_cairo(ctx)
                else:
                    pxb = wall_object['pxb_image_cache']
                    scale = float(self._height) * wall_scale / \
                            float(pxb.get_height())
                    width = int(pxb.get_width() * scale)
                    height = int(pxb.get_height() * scale)

                    # verify if is out of the clip area
                    if wall_x + width < clip_x or \
                        wall_x > clip_x + clip_width or \
                        wall_y + height < clip_y or \
                        wall_y > clip_y + clip_height:
                        break
                    logging.error('Drawing object %s at %d %d w %d h %d',
                            image_file_name, wall_x, wall_y, width, height)

                    ctx.translate(wall_x, wall_y)
                    ctx.scale(scale, scale)
                    Gdk.cairo_set_source_pixbuf(ctx, pxb, 0, 0)
                    ctx.paint()
                wall_object['width'] = width
                wall_object['height'] = height

                if self.view_mode == self.MODE_EDIT and \
                    self.selected is not None and \
                    self.selected.data['original'] == wall_object['original']:
                    # draw controls
                    ctx.set_line_width(WIDTH_CONTROL_LINES)
                    ctx.set_source_rgb(1, 1, 1)
                    ctx.rectangle(wall_x - 2, wall_y - 2,
                            width + 4, height + 4)
                    ctx.stroke()
                    ctx.set_source_rgb(1, 1, 1)
                    ctx.rectangle(wall_x - RESIZE_HANDLE_SIZE / 2,
                            wall_y - RESIZE_HANDLE_SIZE / 2,
                            RESIZE_HANDLE_SIZE, RESIZE_HANDLE_SIZE)
                    ctx.stroke()
                ctx.restore()

    def _get_door_x(self):
        if self.direction in ('N', 'W'):
            # door is at rigth of the wall
            return self._width - self._grid_size * (self._door_width + 2)
        else:
            return self._grid_size * 2

    def _get_door_y(self):
        return self._height - self._grid_size * (self._door_height + 1)

    def draw_door(self, ctx, x, doors):
        y = self._get_door_y()
        ctx.rectangle(x, y, self._grid_size * self._door_width,
                self._grid_size * self._door_height)
        fill = (style.Color('#8B6914').get_rgba())
        stroke = (0, 0, 0)
        ctx.set_source_rgba(*fill)
        ctx.fill_preserve()
        ctx.set_source_rgb(*stroke)
        ctx.stroke()

        # frame
        frame_width = self._grid_size * self._door_width / 8
        fill = (style.Color('#6B4904').get_rgba())
        ctx.set_source_rgba(*fill)
        ctx.rectangle(x, y, self._grid_size * self._door_width, frame_width)
        ctx.fill()
        ctx.rectangle(x, y, frame_width, self._grid_size * self._door_height)
        ctx.fill()
        ctx.rectangle(x + self._grid_size * self._door_width - frame_width, y,
                frame_width, self._grid_size * self._door_height)
        ctx.fill()

        # handle
        if self.direction in ('N', 'W'):
            # door is at rigth of the wall
            x_handle = x + frame_width * 1.5
        else:
            x_handle = x + self._grid_size * self._door_width - \
                    frame_width * 2.5
        y_handle = y + self._grid_size * self._door_height / 2

        ctx.rectangle(x_handle, y_handle, frame_width, frame_width / 4)
        ctx.fill()

        # draw room name
        room_key = self._game_map.get_next_room(self.x, self.y, self.direction)
        room_name = self._game_map.get_room_name(room_key)
        if room_name != '':
            x_text = x + self._grid_size * self._door_width / 2
            y_text = y + self._grid_size * self._door_height / 4
            door_info = self._game_map.get_door_info(doors[0], self.direction)
            if 'room_name' in door_info:
                # check if the room  name has changed
                if door_info['room_name'] != room_name:
                    door_info = {}
            if 'font_size' in door_info:
                font_size = door_info['font_size']
                logging.error('take font_size from door_info %d', font_size)
            else:
                max_width = self._grid_size * self._door_width / 2
                font_size = self.calculate_font_size(ctx, max_width, room_name)
                door_info['font_size'] = font_size
                door_info['room_name'] = room_name
                self._game_map.set_door_info(doors[0], self.direction,
                        door_info)
                self.update_wall_info(self.x, self.y, self.direction,
                        redraw=False)
            self.draw_centered_text(ctx, x_text, y_text, room_name, font_size)

    def calculate_font_size(self, ctx, max_width, text):
        # get the widest row
        font_size = 20
        ctx.set_font_size(font_size)
        widest_row = ''
        max_row_width = 0
        rows = text.split()
        for row in rows:
            xbearing, ybearing, width, height, xadvance, yadvance = \
                    ctx.text_extents(row)
            if width > max_row_width:
                widest_row = row
                max_row_width = width
        # calculate font size
        xbearing, ybearing, width, height, xadvance, yadvance = \
                ctx.text_extents(widest_row)

        while width > max_width:
            font_size -= 1
            ctx.set_font_size(font_size)
            xbearing, ybearing, width, height, xadvance, yadvance = \
                    ctx.text_extents(widest_row)
        return font_size

    def draw_centered_text(self, ctx, x, y, text, font_size, with_border=True):
        ctx.set_font_size(font_size)
        rows = text.split()

        # calc text size
        if with_border:
            ctx.save()
            text_width = 0
            text_height = 0
            for i, row in enumerate(rows):
                logging.error('row "%s"', row)
                xbearing, ybearing, width, height, xadvance, yadvance = \
                ctx.text_extents(row.replace(" ", "-"))
                text_height = text_height + height
                if width > text_width:
                    text_width = width
            margin = self._grid_size * self._door_width / 12
            ctx.rectangle(x - text_width / 2 - margin,
                    y - (text_height / 2),
                    text_width + margin * 2, text_height + margin)
            ctx.set_source_rgb(1, 1, 1)
            ctx.fill_preserve()
            ctx.set_source_rgb(0, 0, 0)
            ctx.stroke()
            ctx.restore()

        ctx.set_source_rgb(0, 0, 0)
        for i, row in enumerate(rows):
            xbearing, ybearing, width, height, xadvance, yadvance = \
            ctx.text_extents(row.replace(" ", "-"))
            ctx.move_to(x - width / 2, y + (i - len(rows) / 2 + 1) * height)
            ctx.show_text(row)
        ctx.stroke()


def show_position(nav_view, x, y, direction, top_view):
    top_view.show_position(x, y, direction)


def main():
    window = Gtk.Window()
    game_map = GameMap()
    nav_view = MapNavView(game_map)
    top_view = mapview.TopMapView(game_map, 200, 200)
    top_view.show_position(nav_view.x, nav_view.y, nav_view.direction)
    nav_view.connect('position-changed', show_position, top_view)
    hbox = Gtk.HBox()
    hbox.pack_start(nav_view, True, True)
    hbox.pack_start(top_view, False, False)
    window.add(hbox)
    nav_view.grab_focus()
    window.connect("destroy", Gtk.main_quit)
    window.set_default_size(800, 600)
    window.show_all()
    Gtk.main()

if __name__ == "__main__":
    main()

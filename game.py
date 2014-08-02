#!/usr/bin/python
import os
import math
import json

import pygame
from gi.repository import Gtk

DATA_DIR = 'images'
STROKE_COLOR = 0, 0, 0  # black
FILL_COLOR = 255, 255, 255  # white
KEY_COLOR = 0, 255, 255  # cyan
BACKGROUND_COLOR = 10, 10, 10  # dark gray
FRAMES_PER_SECOND = 12
SCREEN_SIZE = 320, 240
AT_2X_SCALE = False
DEBUG = False


class ImageManager(object):
    def __init__(self):
        self.images = {}

    def _load_image(self, name, set_keycolor=False):
        image_filename = name + '.png'
        image_path = os.path.join(DATA_DIR, image_filename)
        image = pygame.image.load(image_path)
        image = image.convert()
        if set_keycolor:
            image.set_colorkey(KEY_COLOR)
        if AT_2X_SCALE:
            image = pygame.transform.scale2x(image)
        return image

    def get_image(self, name, colors=None, set_keycolor=False):
        """Get an image by name, load it if necessary.

        If the image wasn't get previously, load it from the
        filesystem.  The next time it is asked, the load will not be
        made.

        If colors are given, return a copy of the image, colorized
        with stroke and fill colors.

        If set_keycolor is True, the KEY_COLOR color will become
        transparent in the image.

        """
        image = self.images.get(name)
        if image is None:
            image = self._load_image(name, set_keycolor)
            self.images[name] = image

        if colors is None:
            return image
        else:
            new_image = image.copy()
            stroke_color, fill_color = colors
            pixel_array = pygame.PixelArray(new_image)
            pixel_array.replace(FILL_COLOR, fill_color, 0.1)
            pixel_array.replace(STROKE_COLOR, stroke_color, 0.1)
            return new_image


IMAGE_MANAGER = ImageManager()


def _load_animation_data(name):
    """Return the animation metadata parsing a text file."""
    data_filename = name + '.json'
    data_path = os.path.join(DATA_DIR, data_filename)
    f = open(data_path, 'rb')
    reader = json.load(f)
    displacement = reader['displacement']
    frames_data = []
    for frame in list(reader['frames']):
        area = frame[:4]
        delta = list(frame[4:])
        frames_data.append({'area': area, 'delta': delta})
    return frames_data, displacement


class CharacterAnimation(object):
    def __init__(self, name, colors=None, set_keycolor=True):
        self._frames_image = IMAGE_MANAGER.get_image(name,
                                                     colors, set_keycolor)
        self._frames_image_mirror = pygame.transform.flip(self._frames_image,
                                                          True, False)
        self._frames_data, self._displacement = _load_animation_data(name)
        if AT_2X_SCALE:
            self._resize_frames_data()
        self._convert_frames_data()
        self._mirror_frames_data()
        self._frames_len = len(self._frames_data)
        self._cur_frame = None
        self._is_playing = None
        self._direction = None
        self._mirror = None

    def _resize_frames_data(self):
        """ Multiply the area data by two.

        This needs to be done if displaying images at 2x.

        """
        for data in self._frames_data:
            area = data['area']
            resized_area = tuple((elem * 2 for elem in area))
            data['area'] = resized_area

    def _convert_frames_data(self):
        """Convert the area data to pygame rects."""
        for data in self._frames_data:
            area = data['area']
            converted_area = pygame.Rect(*area)
            data['area'] = converted_area

    def _mirror_frames_data(self):
        self._frames_data_mirror = []
        for data in self._frames_data:
            mirror_data = {}
            mirror_data['area'] = data['area'].copy()
            mirror_data['area'].left = self._frames_image.get_width() \
                                       - data['area'].left - data['area'].width
            mirror_data['delta'] = list(data['delta'])
            mirror_data['delta'][0] = -data['delta'][0] - data['area'].width
            self._frames_data_mirror.append(mirror_data)

    def play(self, origin=(0, 0), direction='forward', mirror=False):
        self._origin = origin
        if direction == 'forward':
            self._cur_frame = 0
        elif direction == 'backward':
            self._cur_frame = self._frames_len - 1
        else:
            raise NotImplementedError
        self._direction = direction
        self._mirror = mirror
        self._is_playing = True

    def stop(self):
        self._is_playing = False

    def get_dist_to_rect(self):
        if self._mirror:
            data = self._frames_data_mirror[self._cur_frame]
        else:
            data = self._frames_data[self._cur_frame]
        dx = data['delta'][0] + (data['area'].width / 2.0)
        return dx, 0

    def _at_last_frame(self):
        return self._cur_frame == self._frames_len - 1

    def _at_first_frame(self):
        return self._cur_frame == 0

    def _next_frame(self):
        if ((self._direction == 'forward' and self._at_last_frame()) or
            (self._direction == 'backward' and self._at_first_frame())):
            self._is_playing = False
            return 'finished'
        if self._direction == 'forward':
            self._cur_frame += 1
        elif self._direction == 'backward':
            self._cur_frame -= 1

    def update(self):
        if self._is_playing:
            return self._next_frame()

    def draw(self, surface):
        if not self._mirror:
            cur_frame_data = self._frames_data[self._cur_frame]
            frames_image = self._frames_image
        else:
            cur_frame_data = self._frames_data_mirror[self._cur_frame]
            frames_image = self._frames_image_mirror
        area = cur_frame_data['area']
        delta = cur_frame_data['delta']
        dx = self._origin[0] + delta[0]
        dy = self._origin[1] + delta[1]
        return surface.blit(frames_image, (dx, dy), area)

    def get_displacement(self):
        """Return the absolute displacement.

        Takes into account the direction and if the animation is
        mirrored.

        """
        result = None
        if self._direction == 'forward':
            result = self._displacement
        elif self._direction == 'backward':
            result = list((elem * -1 for elem in self._displacement))

        if self._mirror:
            result = -1 * result[0], result[1]

        return result


class Stage(object):
    """A stage contains a wall and a floor."""
    def __init__(self, horizon):
        """Stage constructor.

        Horizon is a number between 0 and 1 that is used to draw the
        wall and the floor above and below a line.

        """
        self._wall = IMAGE_MANAGER.get_image('wall_tile')
        self._floor = IMAGE_MANAGER.get_image('floor_tile')
        self._horizon = horizon

    def draw(self, surface):
        """Draw the wall and the floor.

        The wall and the floor are drawn using tiles.

        """
        surface_width = surface.get_width()
        surface_height = surface.get_height()
        tile_width = self._wall.get_width()
        tile_height = self._wall.get_height()
        wall_height = surface_height * (1.0 - self._horizon)
        floor_height = surface_height * self._horizon

        def get_tiles_to_fill(distance, tile_length):
            """Return the number of tiles needed to fill the distance"""
            return int(math.ceil(float(distance) / tile_length))

        tiles_per_width = get_tiles_to_fill(surface_width, tile_width)
        wall_tiles_per_height = get_tiles_to_fill(wall_height, tile_width)
        floor_tiles_per_height = get_tiles_to_fill(floor_height, tile_width)

        # draw wall above horizon
        for tile_x in range(tiles_per_width):
            dx = tile_width * tile_x
            for tile_y in range(wall_tiles_per_height):
                dy = wall_height - (tile_height * (tile_y + 1))
                surface.blit(self._wall, (dx, dy))

        # draw floor below horizon
        for tile_x in range(tiles_per_width):
            dx = tile_width * tile_x
            for tile_y in range(floor_tiles_per_height):
                dy = wall_height + (tile_height * tile_y)
                surface.blit(self._floor, (dx, dy))


class Character(object):
    def __init__(self, pos_x, pos_y, direction=None, orientation=None):
        self._pos_x = pos_x
        self._pos_y = pos_y
        self._animations = {}
        self._cur_animation = None
        self._on_loop = True
        if orientation is None:
            orientation = 'right'
        self.orientation = orientation
        if direction is None:
            direction = 'forward'
        self.direction = direction

    def add_action(self, animation_name, animation):
        self._animations[animation_name] = animation

    def act(self, animation, clean=True):
        """
        Play the given animation.

        The animation parameter can be an animation name, previously
        passed to the add_animation method, or the animation itself.

        """
        if self._cur_animation is not None and clean:

            self._cur_animation.stop()
            dx, dy = self._cur_animation.get_dist_to_rect()
            self._pos_x += dx
            self._pos_y += dy
        if isinstance(animation, str):
            self._cur_animation = self._animations[animation]
        else:
            self._cur_animation = animation
        origin = (self._pos_x, self._pos_y)
        mirror = self.orientation == 'left'
        self._cur_animation.play(origin, self.direction, mirror)

    def draw(self, surface):
        return self._cur_animation.draw(surface)

    def update(self):
        result = self._cur_animation.update()
        if result == 'finished':
            displacement = self._cur_animation.get_displacement()
            self._pos_x += displacement[0]
            self._pos_y += displacement[1]
            if self._on_loop:
                self.act(self._cur_animation, clean=False)

    def flip_direction(self):
        if self.direction == 'backward':
            self.direction = 'forward'
        elif self.direction == 'forward':
            self.direction = 'backward'


class Game(object):
    """Ingenium Machina game"""
    def __init__(self, colors=None):

        self._running = True
        self._clock = pygame.time.Clock()
        self._background = None
        self._char = None
        self._click_x = None
        self._colors = colors
        if self._colors is not None:
            self._convert_colors()

    def _convert_colors(self):
        """Convert the given colors to pygame colors."""
        self._colors = list((pygame.Color(color) for color in self._colors))

    def setup(self):
        """Setup the game elements."""
        screen = pygame.display.get_surface()

        # graphics that don't move get blitted in this surface
        self._background = screen.copy()

        horizon = 1.0 / 5
        self._stage = Stage(horizon)

        char_pos_x = screen.get_width() / 2
        char_pos_y = screen.get_height() * (1 - horizon)
        self._char = Character(char_pos_x, char_pos_y)
        stand_ani = CharacterAnimation('stand', self._colors)
        self._char.add_action('stand', stand_ani)
        walk_ani = CharacterAnimation('walk', self._colors)
        self._char.add_action('walk', walk_ani)
        self._char.act('stand')

    def run(self):
        """Game loop."""
        self.setup()

        screen = pygame.display.get_surface()

        screen.fill(BACKGROUND_COLOR)
        self._stage.draw(self._background)
        screen.blit(self._background, (0, 0))

        pygame.display.flip()

        # a list of the affected screen areas, for updating only those
        self._dirty_rects = []

        while self._running:
            a, b, c, d = pygame.cursors.load_xbm('my_cursor.xbm','my_cursor_mask.xbm')
            pygame.mouse.set_cursor(a, b, c, d)

            # try to stay at the given frames per second
            self._clock.tick(FRAMES_PER_SECOND)

            # pump gtk messages
            while Gtk.events_pending():
                Gtk.main_iteration()

            # pump pygame messages
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self._running = False
                elif event.type == pygame.VIDEORESIZE:
                    pygame.display.set_mode(event.size, pygame.RESIZABLE)
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self._running = False
                    elif event.key == pygame.K_LEFT:
                        self._click_x = None
                        self._char.orientation = 'left'
                        self._char.act('walk')
                    elif event.key == pygame.K_RIGHT:
                        self._click_x = None
                        self._char.orientation = 'right'
                        self._char.act('walk')
                elif event.type == pygame.KEYUP:
                    self._click_x = None
                    self._char.act('stand')
                elif event.type == pygame.MOUSEBUTTONUP:
                    mouse_pos = pygame.mouse.get_pos()
                    self._click_x = mouse_pos[0]
                    if mouse_pos[0] < self._char._pos_x:
                        self._char.orientation = 'left'
                    else:
                        self._char.orientation = 'right'
                    self._char.act('walk')

            # clean the background, filling the affected areas of the
            # screen with the background
            self._old_dirty_rects = []
            for rect in self._dirty_rects:
                old_rect = screen.blit(self._background, rect, rect)
                self._old_dirty_rects.append(old_rect)

            self._dirty_rects = []

            # move graphics
            if self._click_x is not None:
                stop_animation = False
                if self._char.orientation == 'right':
                    if self._char._pos_x > self._click_x:
                        stop_animation = True
                elif self._char.orientation == 'left':
                    if self._char._pos_x < self._click_x:
                        stop_animation = True
                if stop_animation:
                    self._char.act('stand')
                    self._click_x = None
            self._char.update()

            # draw char
            rect = self._char.draw(screen)
            self._dirty_rects.append(rect)

            # update the display
            pygame.display.update(self._dirty_rects + self._old_dirty_rects)


def main():
    """Setup pygame and run game.

    This function is called when the game is run directly from the
    command line as: ./game.py

    """
    pygame.init()
    pygame.display.set_mode((0, 0), pygame.RESIZABLE)

    colors = ['#101010', '#ffffff']
    game = Game(colors)
    game.run()

if __name__ == '__main__':
    main()

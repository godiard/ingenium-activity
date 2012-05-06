import logging

import gtk
from gtk import gdk
import gobject
import cairo
import rsvg


class Sprite(object):
    def __init__(self, svg_file, cel_width, cel_height, animation_data):
        self.svg_file = svg_file
        self.cel_width, self.cel_height = cel_width, cel_height
        self.current_animation = None
        self.direction = 1

        self._animation_data = animation_data
        self._current_data = None
        self._animation_index = None

        self.load_svg()

    def load_svg(self):
        self._svg = rsvg.Handle(file=self.svg_file)
        self._svg_width = self._svg.props.width
        """
        # create a cache with the image rendered
        self.cache = cairo.ImageSurface(cairo.FORMAT_ARGB32,
                self._svg.props.width, self._svg.props.height)
        self.cache_context = cairo.Context(self.cache)
        self._svg.render_cairo(self.cache_context)
        self.cache.flush()

        # and another with a flipped render
        self.cache_inv = cairo.ImageSurface(cairo.FORMAT_ARGB32,
                self._svg.props.width, self._svg.props.height)
        self.cache_inv_context = cairo.Context(self.cache_inv)
        self.cache_inv_context.scale(-1, 1)
        self._svg.render_cairo(self.cache_inv_context)
        self.cache_inv.flush()
        """

    def change_animation(self, animation_name, direction=1):
        self.current_animation = animation_name
        self._current_data = self._animation_data[animation_name]
        self._animation_index = 0
        #self.direction = direction
        if self.direction == -1:
            self._current_data = list(reversed(self._current_data))

    def next_frame(self):
        if self._animation_index + 1 == len(self._current_data):
            self._animation_index = 0
        else:
            self._animation_index += 1

    def draw(self, context, dx, dy):
        cel_x, cel_y = self._current_data[self._animation_index]
        context.scale(self.direction, 1)
        #if self.direction == 1:
        #    context.set_source_surface(self.cache)
        #else:
        #    context.set_source_surface(self.cache_inv)
        context.translate(dx, dy)

        context.translate(-cel_x * self.cel_width * self.direction,
                          -cel_y * self.cel_height)
        context.rectangle(cel_x * self.cel_width * self.direction,
                          cel_y * self.cel_height,
                          self.cel_width, self.cel_height)
        if self.direction == -1:
            context.translate(-self._svg_width, 0)
        context.clip()
        #context.paint()
        self._svg.render_cairo(context)


class Character(object):
    def __init__(self, drawing_area):
        super(Character, self).__init__()
        self._drawing_area = drawing_area
        self.speed = 10
        animation_data = {
            'stand': [(0, 0)],
            'walk': [(1, 0), (2, 0), (3, 0), (4, 0),
                     (5, 0), (6, 0), (7, 0), (8, 0)],
        }
        self.sprite = Sprite("images/char_walking.svg",
                             100, 160, animation_data)
        self.sprite.change_animation('walk')

        self.pos = [0, 0]
        self.direction = 1  # -1 for left, 1 for right

    def update(self):
        self.sprite.direction = self.direction
        self.sprite.next_frame()
        """
        if self.direction == 1 and self.pos[0] > 600:
            self.pos[0] += self.sprite.cel_width
            self.direction = -1
            self.sprite.change_animation('walk', -1)
        elif self.direction == -1 and self.pos[0] < 0:
            self.pos[0] -= self.sprite.cel_width
            self.direction = 1
            self.sprite.change_animation('walk')
        else:
        """
        self.pos[0] += self.speed * self.direction
        return (self.pos[0],
                self.pos[1] - self.sprite.cel_height + 10,
                self.sprite.cel_width, self.sprite.cel_height)

    def draw(self, context):
        # draw char
        dx, dy = self.pos[0], self.pos[1] - self.sprite.cel_height + 10
        context.save()

        # for debug write a rectangle around
        context.rectangle(dx, dy, self.sprite.cel_width,
                self.sprite.cel_height)
        stroke = (0, 0, 0)
        context.set_source_rgb(*stroke)
        context.stroke()

        self.sprite.draw(context, dx, dy)
        context.restore()


def main():
    def _destroy_cb(widget, data=None):
        gtk.main_quit()

    window = gtk.Window()
    window.resize(600, 160)
    window.connect("destroy", _destroy_cb)
    window.show()

    draw = Character()
    window.add(draw)
    draw.show()

    gtk.main()


if __name__ == "__main__":
    main()

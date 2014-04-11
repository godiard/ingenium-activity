#!/usr/bin/env python
# Copyright (C) 2011, One Laptop Per Child
# Author, Gonzalo Odiard
# License: LGPLv2
#
# The class StateView draw how many questions there are in the game,
# how many have been read, and how many have been replied.

from gi.repository import Gtk
from gi.repository import Rsvg
import cairo
import model
import math
import logging


class StateView():

    def __init__(self, model, x, y, cell_size):
        self.model = model
        self._x = x
        self._y = y
        self._cell_size = cell_size
        svg = Rsvg.Handle.new_from_file('./icons/question.svg')
        self._tmp_image = cairo.ImageSurface(cairo.FORMAT_ARGB32,
                svg.props.width, svg.props.height)
        self._tmp_ctx = cairo.Context(self._tmp_image)
        svg.render_cairo(self._tmp_ctx)
        self._svg_width = svg.props.width
        # last values to avoid redraws
        self._last_cant_questions = 0
        self._last_displayed_questions = 0
        self._last_replied_questions = 0

    def draw(self, ctx):
        # calculate cell size
        cant_questions = len(self.model.data['questions'])
        if cant_questions == 0:
            return

        state = self.model.data['state']
        displayed_questions = len(state['displayed_questions'])
        replied_questions = len(state['replied_questions'])

        if self._last_cant_questions != cant_questions or \
                self._last_displayed_questions != displayed_questions or \
                self._last_replied_questions != replied_questions:
            self._last_cant_questions = cant_questions
            self._last_displayed_questions = displayed_questions
            self._last_replied_questions = replied_questions
        else:
            return
        scale = float(self._svg_width) / float(self._cell_size)
        logging.error('draw stateview scale %s', scale)
        ctx.save()
        ctx.translate(self._x, self._y)
        for n in range(cant_questions):
            if n < replied_questions:
                radio = self._cell_size / 2.0
                ctx.arc(radio, radio, radio, 0., 2 * math.pi)
                ctx.set_source_rgb(0.913, 0.733, 0.0)  # eebb00
                ctx.fill()

            ctx.scale(1.0 / scale, 1.0 / scale)
            ctx.set_source_surface(self._tmp_image)
            if n < displayed_questions:
                ctx.paint()
            else:
                ctx.paint_with_alpha(0.25)
            ctx.scale(scale, scale)
            ctx.translate(self._cell_size, 0)
        ctx.restore()


def main():
    window = Gtk.Window()
    _model = model.GameModel()
    state_view = StateView(_model, 10, 10, 20)
    area = Gtk.DrawingArea()

    # add fake questions to test
    _model.data['questions'].append('')
    _model.data['questions'].append('')
    _model.data['questions'].append('')
    _model.data['questions'].append('')
    _model.data['questions'].append('')

    # ...and a fake state
    state = {'displayed_questions': 3, 'replied_questions': 2}
    _model.data['state'] = state

    def expose(widget, event, state_view):
        ctx = widget.window.cairo_create()
        state_view.draw(ctx)
        return False

    area.connect('expose_event', expose, state_view)

    window.add(area)
    window.connect("destroy", Gtk.main_quit)
    window.show_all()
    Gtk.main()

if __name__ == "__main__":
    main()

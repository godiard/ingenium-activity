# -*- coding: utf-8 -*-
# Copyright 2011 Manuel Quiñones
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

"""Ingenium Machina: an educational game."""

import sys

import gtk
import logging

from gettext import gettext as _

from sugar import profile
from sugar.activity import activity
from sugar.graphics.toolbarbox import ToolbarBox
from sugar.graphics.xocolor import XoColor
from sugar.activity.widgets import ActivityButton
from sugar.activity.widgets import TitleEntry
from sugar.activity.widgets import StopButton
from sugar.activity.widgets import ShareButton

sys.path.append('..')  # import sugargame package from top directory.
import sugargame.canvas

import game


class IngeniumMachinaActivity(activity.Activity):
    """IngeniumMachinaActivity class as specified in activity.info"""

    def __init__(self, handle):
        """Set up the IngeniumMachina activity."""
        activity.Activity.__init__(self, handle)

        # we do not have collaboration features
        # make the share option insensitive
        self.max_participants = 1

        # build the activity toolbar
        self.build_toolbar()

        # build the Pygame canvas
        self._pygamecanvas = sugargame.canvas.PygameCanvas(self)

        # note that set_canvas implicitly calls read_file when
        # resuming from the Journal
        self.set_canvas(self._pygamecanvas)

        # assign keyboard focus to the PygameCanvas widget, so that
        # keyboard events generate pygame events
        self._canvas.grab_focus()

        # create the game instance
        xo_color = XoColor(profile.get_color())
        colors = xo_color.get_stroke_color(), xo_color.get_fill_color()
        self.game = game.Game(colors)

        # start the game running (self.game.run is called when the
        # activity constructor returns).
        self._pygamecanvas.run_pygame(self.game.run)

    def build_toolbar(self):
        toolbar_box = ToolbarBox()

        activity_button = ActivityButton(self)
        toolbar_box.toolbar.insert(activity_button, 0)
        activity_button.show()

        title_entry = TitleEntry(self)
        toolbar_box.toolbar.insert(title_entry, -1)
        title_entry.show()

        share_button = ShareButton(self)
        toolbar_box.toolbar.insert(share_button, -1)
        share_button.show()

        separator = gtk.SeparatorToolItem()
        separator.props.draw = False
        separator.set_expand(True)
        toolbar_box.toolbar.insert(separator, -1)
        separator.show()

        stop_button = StopButton(self)
        toolbar_box.toolbar.insert(stop_button, -1)
        stop_button.show()

        self.set_toolbar_box(toolbar_box)
        toolbar_box.show()

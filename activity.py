# -*- coding: UTF-8 -*-
# Copyright 2011 Gonzalo Odiard, Manuel Quiñones
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

import gtk
import logging

from gettext import gettext as _

from sugar.activity import activity
from sugar.graphics.toolbarbox import ToolbarBox
from sugar.activity.widgets import ActivityToolbarButton
from sugar.activity.widgets import StopButton
from sugar.graphics.toolbutton import ToolButton
from sugar.graphics.radiotoolbutton import RadioToolButton
from sugar.graphics.toggletoolbutton import ToggleToolButton

from model import GameModel
from resources import CollectResourcesWin
from questions import PrepareQuestionsWin
from editmap import EditMapWin
from mapnav import MapNavView
from game_map import GameMap
from dialogs import ResourceDialog, QuestionDialog

PLAY_MODE = 0
EDIT_MODE = 1

EDIT_RESOURCES_ACTION = 1
EDIT_QUESTIONS_ACTION = 2
EDIT_MAP_ACTION = 3
EDIT_DESCRIPTIONS_ACTION = 4


class IngeniumMachinaActivity(activity.Activity):
    """IngeniumMachinaActivity class as specified in activity.info"""

    def __init__(self, handle):
        self.model = GameModel()

        activity.Activity.__init__(self, handle)

        # we do not have collaboration features
        # make the share option insensitive
        self.max_participants = 1

        self.toolbar_box = ToolbarBox()

        activity_button = ActivityToolbarButton(self)
        self.toolbar_box.toolbar.insert(activity_button, 0)

        self._edit_button = ToggleToolButton('view-source')
        self._edit_button.set_tooltip(_('Edit game'))
        self._edit_button.set_active(False)
        self.toolbar_box.toolbar.insert(self._edit_button, -1)

        self._edit_button.connect('toggled', self.__change_mode_cb)

        tool_group = None

        self._resources_button = self._insert_radio(tool_group, 'action_1',
                _('Collect information'))
        self._resources_button.connect('clicked', self.__resources_button_cb)
        tool_group = self._resources_button

        self._questions_button = self._insert_radio(tool_group, 'action_2',
                _('Prepare questions'))
        self._questions_button.connect('clicked', self.__questions_button_cb)

        self._map_button = self._insert_radio(tool_group, 'action_3',
                _('Construct map'))
        self._map_button.connect('clicked', self.__map_button_cb)

        self._descriptions_button = self._insert_radio(tool_group, 'action_4',
                _('Write descriptions'))
        self._descriptions_button.connect('clicked',
                self.__descriptions_button_cb)

        self.toolbar_box.toolbar.insert(gtk.SeparatorToolItem(), -1)

        self._add_button = ToolButton('add')
        self._add_button.connect('clicked', self.__add_cb)
        self.toolbar_box.toolbar.insert(self._add_button, -1)

        self._remove_button = ToolButton('remove')
        self._remove_button.connect('clicked', self.__remove_cb)
        self.toolbar_box.toolbar.insert(self._remove_button, -1)

        separator = gtk.SeparatorToolItem()
        separator.props.draw = False
        separator.set_expand(True)
        self.toolbar_box.toolbar.insert(separator, -1)
        separator.show()

        stop_button = StopButton(self)
        self.toolbar_box.toolbar.insert(stop_button, -1)
        stop_button.show()

        self.set_toolbar_box(self.toolbar_box)
        self.toolbar_box.show_all()

        # init edition windows
        self.collect_resources_win = None
        self.prepare_questions_win = None
        self.edit_map_win = None
        self.edit_descriptions_win = None

        # init game
        self.activity_mode = PLAY_MODE
        self.action = EDIT_RESOURCES_ACTION
        self.update_buttons_state()
        self.main_notebook = gtk.Notebook()

        self.main_notebook.set_show_tabs(False)
        self.main_notebook.show_all()
        self.set_canvas(self.main_notebook)

        if handle.object_id is None:
            self.main_notebook.append_page(self.create_play_view())

    def create_play_view(self):
        if not 'map_data' in self.model.data or \
            self.model.data['map_data'] is None:
            self.game_map = GameMap()
        else:
            self.game_map = GameMap(self.model.data['map_data'])
        self.mapnav_game = MapNavView(self.game_map, self.model)
        self.mapnav_game.show()
        self.mapnav_game.connect('resource-clicked',
                self.__resource_clicked_cb)
        self.mapnav_game.connect('question-clicked',
                self.__question_clicked_cb)
        return self.mapnav_game

    def __change_mode_cb(self, button):
        if button.get_active():
            self.activity_mode = EDIT_MODE
            if self.action == EDIT_RESOURCES_ACTION:
                self.__resources_button_cb(self._resources_button)
            elif self.action == EDIT_QUESTIONS_ACTION:
                self.__questions_button_cb(self._questions_button)
            elif self.action == EDIT_DESCRIPTIONS_ACTION:
                self.__descriptions_button_cb(self._descriptions_button)
            else:
                self.main_notebook.set_current_page(0)

        else:
            self.activity_mode = PLAY_MODE
            self.main_notebook.set_current_page(0)
            self.mapnav_game.clear_cache()
        self.update_buttons_state()

    def __add_cb(self, button):
        if self.action is None:
            return
        if self.action == EDIT_RESOURCES_ACTION:
            self.collect_resources_win.add_resource()
        elif self.action == EDIT_QUESTIONS_ACTION:
            self.prepare_questions_win.add_question()
        elif self.action == EDIT_MAP_ACTION:
            self.edit_map_win.add_selected_object()

    def __remove_cb(self, button):
        if self.action is None:
            return
        if self.action == EDIT_RESOURCES_ACTION:
            self.collect_resources_win.del_resource()
        elif self.action == EDIT_QUESTIONS_ACTION:
            self.prepare_questions_win.del_question()
        elif self.action == EDIT_MAP_ACTION:
            self.edit_map_win.remove_selected_object()

    def update_buttons_state(self):
        edit_mode = self.activity_mode == EDIT_MODE
        self._resources_button.set_sensitive(edit_mode)
        self._questions_button.set_sensitive(edit_mode)
        self._map_button.set_sensitive(edit_mode)
        self._descriptions_button.set_sensitive(edit_mode)
        self._add_button.set_sensitive(edit_mode)
        self._remove_button.set_sensitive(edit_mode)

    def _insert_radio(self, group, icon_name, label):
        button = RadioToolButton()
        button.props.group = group
        button.props.icon_name = icon_name
        button.set_tooltip(label)
        self.toolbar_box.toolbar.insert(button, -1)
        return button

    def __questions_button_cb(self, button):
        if self.prepare_questions_win is None:
            self.prepare_questions_win = PrepareQuestionsWin(self)
            button.page = self.main_notebook.get_n_pages()
            self.main_notebook.append_page(self.prepare_questions_win)
            self.prepare_questions_win.connect('question_updated',
                    self.__question_updated_cb)
        self.main_notebook.set_current_page(button.page)
        self.action = EDIT_QUESTIONS_ACTION

    def __resources_button_cb(self, button):
        if self.collect_resources_win is None:
            self.collect_resources_win = CollectResourcesWin(self)
            button.page = self.main_notebook.get_n_pages()
            self.main_notebook.append_page(self.collect_resources_win)
            # connect signal to know if the resources are updated
            self.collect_resources_win.connect('resource_updated',
                    self.__resources_updated_cb)
        self.main_notebook.set_current_page(button.page)
        self.action = EDIT_RESOURCES_ACTION

    def __resources_updated_cb(self, origin):
        logging.error('** Resources updated signal')
        if self.edit_map_win is not None:
            self.edit_map_win.load_resources_and_questions()

    def __question_updated_cb(self, origin):
        logging.error('** Questions updated signal')
        if self.edit_map_win is not None:
            self.edit_map_win.load_resources_and_questions()

    def __map_button_cb(self, button):
        if self.edit_map_win is None:
            self.edit_map_win = EditMapWin(self.model)
            button.page = self.main_notebook.get_n_pages()
            self.main_notebook.append_page(self.edit_map_win)

            # Try connect with the playing map
            logging.error('Connecting signal map-updated')
            self.edit_map_win.nav_view.connect('map-updated',
                self.mapnav_game.receive_update_wall_info)

        self.main_notebook.set_current_page(button.page)
        self.action = EDIT_MAP_ACTION

    def __descriptions_button_cb(self, button):
        if self.edit_descriptions_win is None:
            self.edit_descriptions_win = gtk.HBox()

            button.page = self.main_notebook.get_n_pages()
            self.main_notebook.append_page(self.edit_descriptions_win)
            # connect signal to know if the resources are updated

        self.main_notebook.set_current_page(button.page)
        self.action = EDIT_DESCRIPTIONS_ACTION

    def __resource_clicked_cb(self, mapnav, id_resource):
        logging.error('** Resource %s clicked', id_resource)
        resource_dialog = ResourceDialog(self.model, id_resource)
        resource_dialog.set_transient_for(self.get_toplevel())
        resource_dialog.show_all()

    def __question_clicked_cb(self, mapnav, id_question):
        logging.error('** Question %s clicked', id_question)
        question_dialog = QuestionDialog(self.model, id_question)
        question_dialog.set_transient_for(self.get_toplevel())
        question_dialog.connect('reply-selected', self.__question_replied_cb)
        question_dialog.show_all()
        self.model.register_displayed_question(id_question)

    def __question_replied_cb(self, dialog, id_question, valid):
        logging.error('** Question %s replied %s', id_question, valid)
        if valid:
            self.model.register_replied_question(id_question)

    def read_file(self, file_path):
        '''Read file from Sugar Journal.'''
        logging.error('READING FILE %s', file_path)
        self.model.read(file_path)
        self.main_notebook.append_page(self.create_play_view())

    def write_file(self, file_path):
        '''Save file on Sugar Journal. '''
        logging.error('WRITING FILE %s', file_path)
        self.metadata['mime_type'] = 'application/x-ingenium-machine'
        self.model.write(file_path)


class CollectInformationWin(gtk.VBox):

    def __init__(self):
        gtk.VBox.__init__(self)
        self.introduction = gtk.Label(_('Edit your Adventure Game in 4 steps'))
        self.pack_start(self.introduction, False)

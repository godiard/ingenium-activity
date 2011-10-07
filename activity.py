# Copyright 2011 Gonzalo Odiard
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
import gobject
import logging

from gettext import gettext as _

from sugar.activity import activity
from sugar.graphics.toolbarbox import ToolbarBox
from sugar.activity.widgets import ActivityToolbarButton
from sugar.activity.widgets import StopButton
from sugar.graphics.toolbutton import ToolButton
from sugar.graphics.radiotoolbutton import RadioToolButton
from sugar.graphics.toggletoolbutton import ToggleToolButton
from sugar.graphics.icon import Icon

PLAY_MODE = 0
EDIT_MODE = 1

EDIT_INFORMATION_ACTION = 1
EDIT_QUESTIONS_ACTION = 2
EDIT_MAP_ACTION = 3
EDIT_DESCRIPTIONS_ACTION = 4


class IngeniumMachinaActivity(activity.Activity):
    """IngeniumMachinaActivity class as specified in activity.info"""

    def __init__(self, handle):
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

        self._collect_button = self._insert_radio(tool_group, 'action_1',
                _('Collect information'))
        tool_group = self._collect_button

        self._questions_button = self._insert_radio(tool_group, 'action_2',
                _('Prepare questions'))
        self._questions_button.connect('clicked', self.__questions_button_cb)

        self._map_button = self._insert_radio(tool_group, 'action_3',
                _('Construct map'))

        self._descriptions_button = self._insert_radio(tool_group, 'action_4',
                _('Write descriptions'))

        self.toolbar_box.toolbar.insert(gtk.SeparatorToolItem(), -1)

        self._add_button = ToolButton('add')
        #self._add_button.connect('clicked', self._game_reset_cb)
        self.toolbar_box.toolbar.insert(self._add_button, -1)

        self._remove_button = ToolButton('remove')
        #self._add_button.connect('clicked', self._game_reset_cb)
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

        # init game
        self.mode = PLAY_MODE
        self.update_buttons_state()
        #self.set_canvas(edit_win)

    def __change_mode_cb(self, button):
        if button.get_active():
            self.mode = EDIT_MODE
        else:
            self.mode = PLAY_MODE
        self.update_buttons_state()

    def update_buttons_state(self):
        self._collect_button.set_sensitive(self.mode == EDIT_MODE)
        self._questions_button.set_sensitive(self.mode == EDIT_MODE)
        self._map_button.set_sensitive(self.mode == EDIT_MODE)
        self._descriptions_button.set_sensitive(self.mode == EDIT_MODE)
        self._add_button.set_sensitive(self.mode == EDIT_MODE)
        self._remove_button.set_sensitive(self.mode == EDIT_MODE)

    def _insert_radio(self, group, icon_name, label):
        button = RadioToolButton()
        button.props.group = group
        button.props.icon_name = icon_name
        button.set_tooltip(label)
        self.toolbar_box.toolbar.insert(button, -1)
        return button

    def __questions_button_cb(self, button):
        prepare_questions_win = PrepareQuestionsWin()
        self.set_canvas(prepare_questions_win)


class CollectInformationWin(gtk.VBox):

    def __init__(self):
        gtk.VBox.__init__(self)
        self.introduction = gtk.Label(_('Edit your Adventure Game in 4 steps'))
        self.pack_start(self.introduction, False)


class PrepareQuestionsWin(gtk.HBox):

    def __init__(self):
        gtk.HBox.__init__(self)
        # Listview
        """
        +---------+------------------------------+
        |Listview | Text - Graph -               |
        |         +------------------------------+
        |         | Edit Question Panel          |
        |         | (Notebook with 2 pages,      |
        |         |  one to text, one to graph   |
        +---------+------------------------------+
        """

        # Listview
        self.quest_listview = gtk.TreeView()
        width = int(gtk.gdk.screen_width() / 3)
        self.quest_listview.set_size_request(width, -1)

        self.quest_listview.connect('cursor-changed', self.select_question)
        self.treemodel = gtk.ListStore(gobject.TYPE_STRING)
        self.quest_listview.set_model(self.treemodel)
        renderer = gtk.CellRendererText()
        renderer.set_property('wrap-mode', gtk.WRAP_WORD)
        self.treecol = gtk.TreeViewColumn(_('Questions'), renderer, text=0)
        self.quest_listview.append_column(self.treecol)
        self.tree_scroller = gtk.ScrolledWindow(hadjustment=None,
                vadjustment=None)
        self.tree_scroller.set_policy(gtk.POLICY_NEVER,
                gtk.POLICY_AUTOMATIC)
        self.tree_scroller.add(self.quest_listview)
        self.pack_start(self.tree_scroller, False)

        vbox = gtk.VBox()
        self.pack_start(vbox, True)

        hbox_buttons = gtk.HBox()
        add_reply_button = gtk.Button(_('Add reply'))
        add_reply_button.connect('clicked', self.__add_reply_cb)
        hbox_buttons.pack_start(add_reply_button, False, padding=5)

        vbox.pack_start(hbox_buttons, False, padding=5)

        # edit question panel
        notebook = gtk.Notebook()
        vbox.pack_start(notebook, False)
        self.vbox_edit = gtk.VBox()
        notebook.set_show_tabs(False)
        notebook.append_page(self.vbox_edit)    

        self.vbox_edit.pack_start(gtk.Label(_('Question')), padding=5)
        self.question_entry = gtk.Entry()
        hbox_row = gtk.HBox()
        hbox_row.pack_start(self.question_entry, True, padding=5)
        self.vbox_edit.pack_start(hbox_row, padding=5)

        self.vbox_edit.pack_start(gtk.Label(_('Replies')), padding=5)
        self.replies_entries = []
        self._add_reply_entry()
        self._add_reply_entry(reply_ok=False)

        self.show_all()

    def __add_reply_cb(self, button):
        self._add_reply_entry(reply_ok=False)

    def _add_reply_entry(self, reply_ok=True):
        hbox_row = gtk.HBox()
        reply_entry = gtk.Entry()
        hbox_row.pack_start(reply_entry, True, padding=5)
        self.vbox_edit.pack_start(hbox_row, True, padding=5)
        if reply_ok:
            icon = Icon(icon_name='dialog-ok')
        else:
            icon = Icon(icon_name='dialog-cancel')

        hbox_row.pack_start(icon, False, padding=5)
        hbox_row.show_all()
        self.replies_entries.append(reply_entry)

    def select_question(self):
        pass

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

from model import GameModel

PLAY_MODE = 0
EDIT_MODE = 1

EDIT_INFORMATION_ACTION = 1
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
        self.prepare_questions_win = None

        # init game
        self.mode = PLAY_MODE
        self.action = None
        self.update_buttons_state()
        # fake temporal game cointainer (Manu will replace it)
        # this is crazy, the read_file method is called at the mapping
        # of canvas object
        self.game_cointainer = gtk.HBox()
        self.game_cointainer.show()
        self.set_canvas(self.game_cointainer)

    def __change_mode_cb(self, button):
        if button.get_active():
            self.mode = EDIT_MODE
        else:
            self.mode = PLAY_MODE
            self.game_cointainer
        self.update_buttons_state()

    def __add_cb(self, button):
        if self.action is None:
            return
        if self.action == EDIT_QUESTIONS_ACTION:
            self.prepare_questions_win.add_question()

    def __remove_cb(self, button):
        if self.action is None:
            return
        if self.action == EDIT_QUESTIONS_ACTION:
            self.prepare_questions_win.del_question()

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
        if self.prepare_questions_win is None:
            self.prepare_questions_win = PrepareQuestionsWin(self.model)
        self.set_canvas(self.prepare_questions_win)
        self.action = EDIT_QUESTIONS_ACTION

    def read_file(self, file_path):
        '''Read file from Sugar Journal.'''
        logging.error('READING FILE %s', file_path)
        self.model.read(file_path)

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


class PrepareQuestionsWin(gtk.HBox):

    def __init__(self, model):
        gtk.HBox.__init__(self)
        self.model = model
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
        self.question_entry.connect('changed', self.__information_changed_cb)
        hbox_row = gtk.HBox()
        hbox_row.pack_start(self.question_entry, True, padding=5)
        self.vbox_edit.pack_start(hbox_row, padding=5)

        self.vbox_edit.replies = []  # used to remove the childs
        self.vbox_edit.pack_start(gtk.Label(_('Replies')), padding=5)
        self.replies_entries = []
        #self._add_reply_entry()
        #self._add_reply_entry(reply_ok=False)

        self._load_treemodel()
        self.show_all()
        self._modified_data = False
        self._selected_key = None

    def __information_changed_cb(self, entry):
        logging.debug('Data modified')
        self._modified_data = True

    def _load_treemodel(self):
        logging.error('loading treemodel')
        for question in self.model.data['questions']:
            logging.error('adding question %s', question)
            self.treemodel.append([question['question']])

    def __add_reply_cb(self, button):
        self._add_reply_entry(reply_ok=len(self.replies_entries) == 0)

    def _add_reply_entry(self, reply_ok=True, text=None):
        hbox_row = gtk.HBox()
        reply_entry = gtk.Entry()
        if text is not None:
            reply_entry.set_text(text)
        reply_entry.connect('changed', self.__information_changed_cb)
        hbox_row.pack_start(reply_entry, True, padding=5)
        self.vbox_edit.pack_start(hbox_row, True, padding=5)
        if reply_ok:
            icon = Icon(icon_name='dialog-ok')
        else:
            icon = Icon(icon_name='dialog-cancel')

        hbox_row.pack_start(icon, False, padding=5)
        hbox_row.show_all()
        self.replies_entries.append(reply_entry)
        self.vbox_edit.replies.append(hbox_row)

    def select_question(self, treeview):
        treestore, coldex = treeview.get_selection().get_selected()
        logging.debug('selected question %s', treestore.get_value(coldex, 0))
        if self._modified_data:
            # update data
            self._update_model(self._selected_key)
        self._selected_key = treestore.get_value(coldex, 0)
        self._display_model(self._selected_key)

    def _update_model(self, key):
        question = self._get_question(key)
        new_entry = False
        if question == None:
            question = {}
            new_entry = True
        replies = []
        for reply_entry in self.replies_entries:
            if reply_entry.get_text() != '':
                reply = {}
                reply['text'] = reply_entry.get_text()
                reply['valid'] = len(replies) == 0  # The first is the valid
                replies.append(reply)
        question = {'question': self.question_entry.get_text(),
                    'type': 'TEXT',
                    'replies': replies}
        if new_entry:
            self.model.data['questions'].append(question)
            self.treemodel.append([self.question_entry.get_text()])
        self._modified_data = False

    def _display_model(self, key):
        question = self._get_question(key)
        self._display_question(question)

    def _display_question(self, question, display_empty_entries=False):
        self.question_entry.set_text(question['question'])
        # remove old replies entries
        for hbox in self.vbox_edit.replies:
            self.vbox_edit.remove(hbox)
        self.vbox_edit.replies = []
        # add news
        for reply in question['replies']:
            if display_empty_entries or reply['text'] != '':
                self._add_reply_entry(reply_ok=reply['valid'],
                        text=reply['text'])
        self._modified_data = False

    def _get_question(self, key):
        for question in self.model.data['questions']:
            if question['question'] == key:
                return question
        return None

    def del_question(self):
        logging.debug('del question')
        if self._selected_key is not None:
            logging.debug('select key %s', self._selected_key)
            self.model.data['questions'].remove(self._get_question(
                                                        self._selected_key))
            self.treemodel.remove(
                        self.quest_listview.get_selection())
            self._modified_data = False
            self._selected_key = None

    def add_question(self):
        if self._modified_data:
            # update data
            self._update_model(self._selected_key)

        self._selected_key = None

        question = {'question': '',
                    'type': 'TEXT',
                    'replies': [{'text':'', 'valid':True},
                                {'text':'', 'valid':False}]}
        self._display_question(question, display_empty_entries=True)

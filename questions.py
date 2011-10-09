import gtk
import gobject
import logging

from gettext import gettext as _
from sugar.graphics.icon import Icon

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

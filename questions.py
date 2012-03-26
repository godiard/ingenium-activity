import gtk
import gobject
import logging
import os
import shutil
import cairo

from gettext import gettext as _

from sugar.activity import activity
from sugar.graphics.icon import Icon
from sugar.graphics.objectchooser import ObjectChooser


class DrawReplyArea(gtk.DrawingArea):

    def __init__(self, image_file_name):
        gtk.DrawingArea.__init__(self)
        self._image_file_name = image_file_name
        self.pixbuf = gtk.gdk.pixbuf_new_from_file(image_file_name)
        self._width = self.pixbuf.get_width()
        self._height = self.pixbuf.get_height()

        # Signals used to handle backing pixmap
        self.connect("expose_event", self.__expose_draw_reply_cb)
        # Event signals
        self.connect("motion_notify_event", self.__motion_draw_reply_cp)
        self.connect("button_press_event", self.__button_press_draw_reply_cp)

        self.set_events(gtk.gdk.EXPOSURE_MASK | gtk.gdk.LEAVE_NOTIFY_MASK
                | gtk.gdk.BUTTON_PRESS_MASK | gtk.gdk.POINTER_MOTION_MASK
                | gtk.gdk.POINTER_MOTION_HINT_MASK)
        self.reply_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32,
                self._width, self._height)
        self.background = None
        self.show()

    def setup(self):
        """Configure the Area object."""
        logging.debug('Area.setup: w=%s h=%s' % (self._width, self._height))
        win = self.window
        self.background = gtk.gdk.Pixmap(win, self._width, self._height, -1)
        self.gc = win.new_gc()
        self.pixbuf.render_to_drawable(self.background, self.gc, 0, 0, 0, 0,
                self._width, self._height, gtk.gdk.RGB_DITHER_NONE, 0, 0)
        self.set_size_request(self._width, self._height)

        return True

    # Redraw the screen from the backing pixmap
    def __expose_draw_reply_cb(self, widget, event):
        if self.background is None:
            self.setup()
        x, y, width, height = event.area
        widget.window.draw_drawable(widget.get_style().fg_gc[gtk.STATE_NORMAL],
                                self.background, x, y, x, y, width, height)
        cr = widget.window.cairo_create()
        cr.rectangle(x, y, width, height)
        cr.clip()
        cr.set_source_surface(self.reply_surface)
        cr.paint()

        return False

    # Draw a rectangle on the screen
    def draw_brush(self, widget, x, y):
        brush_size = 20
        cr = cairo.Context(self.reply_surface)
        cr.set_source_rgb(1, 0, 0)
        cr.rectangle(x - brush_size / 2, y - brush_size / 2, brush_size,
                brush_size)
        #cr.arc(x, y, brush_size, 0, 3.15)
        cr.fill()
        widget.queue_draw_area(x - brush_size / 2, y - brush_size / 2,
                brush_size, brush_size)

    def __button_press_draw_reply_cp(self, widget, event):
        if event.button == 1:
            self.draw_brush(widget, event.x, event.y)
        return True

    def __motion_draw_reply_cp(self, widget, event):
        if event.is_hint:
            x, y, state = event.window.get_pointer()
        else:
            x = event.x
            y = event.y
            state = event.state
        if state & gtk.gdk.BUTTON1_MASK:
            self.draw_brush(widget, x, y)
        return True


class PrepareQuestionsWin(gtk.HBox):

    def __init__(self, activity):
        gtk.HBox.__init__(self)
        self._activity = activity
        self.model = activity.model
        # Listview
        """
        +---------+------------------------------+
        |Listview | Question type:Text - Graph - |
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

        # edit question panel

        vbox.pack_start(gtk.Label(_('Question')), False, padding=5)
        self.question_entry = gtk.Entry()
        self.question_entry.connect('changed', self.__information_changed_cb)
        hbox_row = gtk.HBox()
        hbox_row.pack_start(self.question_entry, True, padding=5)
        vbox.pack_start(hbox_row, False, padding=5)

        notebook = gtk.Notebook()
        vbox.pack_start(notebook, True)
        self.vbox_edit = gtk.VBox()
        notebook.set_show_tabs(True)
        notebook.append_page(self.vbox_edit, gtk.Label(_('Text reply')))

        vbox_graph_replies = gtk.VBox()
        notebook.append_page(vbox_graph_replies, gtk.Label(_('Graph reply')))

        # text reply controls
        hbox_buttons = gtk.HBox()
        add_reply_button = gtk.Button(_('Add reply'))
        add_reply_button.connect('clicked', self.__add_reply_cb)
        hbox_buttons.pack_start(add_reply_button, False, padding=5)

        self.vbox_edit.pack_start(hbox_buttons, False, padding=5)

        self.vbox_edit.replies = []  # used to remove the childs
        self.vbox_edit.pack_start(gtk.Label(_('Replies')), False, padding=5)
        self.replies_entries = []
        #self._add_reply_entry()
        #self._add_reply_entry(reply_ok=False)

        # graph reply
        self.load_image_button = gtk.Button(_('Load Image'))
        self.load_image_button.connect('clicked', self.__load_image_cb)
        vbox_graph_replies.pack_start(self.load_image_button, False, padding=5)

        self.scrollwin = gtk.ScrolledWindow()
        self.scrollwin.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.draw_reply_area = None
        vbox_graph_replies.pack_start(self.scrollwin, True, padding=5)

        help_text = _('After select a image, paint the area where ' +
                'is replied')
        vbox_graph_replies.pack_start(gtk.Label(help_text), False, padding=5)
        self._load_treemodel()
        self.show_all()
        self._modified_data = False
        self._selected_key = None

    def __load_image_cb(self, button):
        try:
            chooser = ObjectChooser(_('Choose image'),
                self._activity, gtk.DIALOG_MODAL |
                gtk.DIALOG_DESTROY_WITH_PARENT, what_filter='Image')
        except:
            chooser = ObjectChooser(_('Choose image'),
                self._activity, gtk.DIALOG_MODAL |
                gtk.DIALOG_DESTROY_WITH_PARENT)
        try:
            result = chooser.run()
            if result == gtk.RESPONSE_ACCEPT:
                logging.debug('ObjectChooser: %r',
                        chooser.get_selected_object())
                jobject = chooser.get_selected_object()
                if jobject and jobject.file_path:
                    self.__load_image(jobject.file_path)
        finally:
            chooser.destroy()
            del chooser

    def __load_image(self, file_path):
        self.draw_reply_area = DrawReplyArea(file_path)
        self.scrollwin.add_with_viewport(self.draw_reply_area)
        # copy to resources directory
        self.model.check_resources_directory()
        resource_path = os.path.join(activity.get_activity_root(),
                'instance', 'resources')
        shutil.copy(file_path, resource_path)
        self._image_resource_path = os.path.join(resource_path,
                os.path.basename(file_path))
        self._modified_data = True

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
        self.vbox_edit.pack_start(hbox_row, False, padding=5)
        if reply_ok:
            icon = Icon(icon_name='dialog-ok')
        else:
            icon = Icon(icon_name='dialog-cancel')

        hbox_row.pack_start(icon, False, padding=5)
        hbox_row.show_all()
        self.replies_entries.append(reply_entry)
        self.vbox_edit.replies.append(hbox_row, False)

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

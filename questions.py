from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GdkPixbuf
from gi.repository import GObject
import logging
import os
import shutil
import cairo

from gettext import gettext as _

from sugar3.activity import activity
from sugar3.graphics.icon import Icon
from sugar3.graphics.objectchooser import ObjectChooser

SMILIES_OK = ['cool', 'grin', 'nerd', 'smile', 'wink']
SMILIES_WRONG = ['sad', 'sick', 'weep']


class DrawReplyArea(Gtk.DrawingArea):

    __gsignals__ = {
        'reply-selected': (GObject.SignalFlags.RUN_LAST, None,
                ([GObject.TYPE_BOOLEAN])),
    }

    def __init__(self, image_file_name, reply_file_name=None, edit=False):
        GObject.GObject.__init__(self)
        self._image_file_name = image_file_name
        self.pixbuf = GdkPixbuf.Pixbuf.new_from_file(image_file_name)
        self._width = self.pixbuf.get_width()
        self._height = self.pixbuf.get_height()
        self._edit = edit

        self.reply_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32,
                self._width, self._height)

        # Signals used to handle backing pixmap
        self.connect("draw", self.__draw_cb)
        # Event signals

        if self._edit:
            self.connect("motion_notify_event", self.__motion_draw_reply_cp)
            self.connect("button_press_event",
                    self.__button_press_draw_reply_cb)
        else:
            self.connect("button_press_event",
                    self.__button_press_check_value_cb)
            if reply_file_name is not None:
                self.reply_surface = \
                    cairo.ImageSurface.create_from_png(reply_file_name)
            else:
                logging.error('ERROR: using in play mode without reply image')

        self.set_events(Gdk.EventMask.EXPOSURE_MASK | Gdk.EventMask.LEAVE_NOTIFY_MASK
                | Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.POINTER_MOTION_MASK
                | Gdk.EventMask.POINTER_MOTION_HINT_MASK)
        self.background = None
        self.show()

    def setup(self):
        """Configure the Area object."""
        logging.debug('Area.setup: w=%s h=%s' % (self._width, self._height))
        win = self.get_window()
        self.background = Gdk.Pixmap(win, self._width, self._height, -1)
        self.gc = win.new_gc()
        self.pixbuf.render_to_drawable(self.background, self.gc, 0, 0, 0, 0,
                self._width, self._height, Gdk.RGB_DITHER_NONE, 0, 0)
        self.set_size_request(self._width, self._height)

        return True

    # Redraw the screen from the backing pixmap
    def __draw_cb(self, widget, ctx):
        if self.background is None:
            self.setup()
        x, y, width, height = ctx.clip_extents()
        widget.get_window().draw_drawable(widget.get_style().fg_gc[Gtk.StateType.NORMAL],
                                self.background, x, y, x, y, width, height)
        if self._edit:
            ctx.rectangle(x, y, width, height)
            ctx.clip()
            ctx.set_source_surface(self.reply_surface)
            ctx.paint()

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

    def __button_press_draw_reply_cb(self, widget, event):
        if event.button == 1:
            self.draw_brush(widget, event.x, event.y)
        return True

    def __button_press_check_value_cb(self, widget, event):
        if event.button == 1:
            x, y = event.x, event.y
            cairo_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 1, 1)
            cairo_context = cairo.Context(cairo_surface)
            # translate xlib_surface so that target pixel is at 0, 0
            cairo_context.set_source_surface(self.reply_surface, -x, -y)
            cairo_context.rectangle(0, 0, 1, 1)
            cairo_context.set_operator(cairo.OPERATOR_SOURCE)
            cairo_context.fill()
            cairo_surface.flush()  # ensure all writing is done
            # Read the pixel
            pixels = cairo_surface.get_data()
            red, green, blue = ord(pixels[2]), ord(pixels[1]), ord(pixels[0])
            #logging.error('Read color %d %d %d', red, green, blue)
            valid_color = (red == 255 and green == 0 and blue == 0)
            self.emit('reply-selected', valid_color)
        return True

    def __motion_draw_reply_cp(self, widget, event):
        if event.is_hint:
            x, y, state = event.window.get_pointer()
        else:
            x = event.x
            y = event.y
            state = event.get_state()
        if state & Gdk.ModifierType.BUTTON1_MASK:
            self.draw_brush(widget, x, y)
        return True

    def write_reply_png(self, file_path):
        self.reply_surface.write_to_png(file_path)

    def read_reply_png(self, file_path):
        self.reply_surface = self.reply_surface.create_from_png(file_path)


class PrepareQuestionsWin(Gtk.HBox):

    __gsignals__ = {
        'question_updated': (GObject.SignalFlags.RUN_FIRST, None, [])
    }

    def __init__(self, activity):
        GObject.GObject.__init__(self)
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
        self.quest_listview = Gtk.TreeView()
        width = int(Gdk.Screen.width() / 3)
        self.quest_listview.set_size_request(width, -1)

        self.quest_listview.connect('cursor-changed', self.select_question)
        self.treemodel = Gtk.ListStore(GObject.TYPE_STRING,
                GObject.TYPE_STRING)
        self.quest_listview.set_model(self.treemodel)
        renderer = Gtk.CellRendererText()
        renderer.set_property('wrap-mode', Gtk.WrapMode.WORD)
        self.treecol = Gtk.TreeViewColumn(_('Questions'), renderer, text=0)
        self.quest_listview.append_column(self.treecol)
        self.tree_scroller = Gtk.ScrolledWindow(hadjustment=None,
                vadjustment=None)
        self.tree_scroller.set_policy(Gtk.PolicyType.NEVER,
                Gtk.PolicyType.AUTOMATIC)
        self.tree_scroller.add(self.quest_listview)
        self.pack_start(self.tree_scroller, False, False, 0)

        vbox = Gtk.VBox()
        self.pack_start(vbox, True, True, 0)

        # edit question panel

        vbox.pack_start(Gtk.Label(_('Question')), False, False, padding=5)
        self.question_entry = Gtk.Entry()
        self.question_entry.connect('changed', self.__information_changed_cb)
        hbox_row = Gtk.HBox()
        hbox_row.pack_start(self.question_entry, True, True, padding=5)
        vbox.pack_start(hbox_row, False, False, padding=5)

        self.notebook = Gtk.Notebook()
        vbox.pack_start(self.notebook, True, True, 0)
        self.vbox_edit = Gtk.VBox()
        self.notebook.set_show_tabs(True)
        self.questions_types = []

        self.notebook.append_page(self.vbox_edit, Gtk.Label(label=_('Text reply')))
        self.questions_types.append(self.model.QUESTION_TYPE_TEXT)

        vbox_graph_replies = Gtk.VBox()
        self.notebook.append_page(vbox_graph_replies,
                Gtk.Label(label=_('Graph reply')))
        self.questions_types.append(self.model.QUESTION_TYPE_GRAPHIC)

        # text reply controls
        hbox_buttons = Gtk.HBox()
        add_reply_button = Gtk.Button(_('Add reply'))
        add_reply_button.connect('clicked', self.__add_reply_cb)
        hbox_buttons.pack_start(add_reply_button, False, False, padding=5)

        self.vbox_edit.pack_start(hbox_buttons, False, False, padding=5)

        self.vbox_edit.replies = []  # used to remove the childs
        self.vbox_edit.pack_start(Gtk.Label(_('Replies')), False, False, padding=5)
        self.replies_entries = []
        #self._add_reply_entry()
        #self._add_reply_entry(reply_ok=False)

        # graph reply
        self.load_image_button = Gtk.Button(_('Load Image'))
        self.load_image_button.connect('clicked', self.__load_image_cb)
        vbox_graph_replies.pack_start(self.load_image_button, False, False, padding=5)

        self.scrollwin = Gtk.ScrolledWindow()
        self.scrollwin.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.draw_reply_area = None
        vbox_graph_replies.pack_start(self.scrollwin, True, False, padding=5)

        help_text = _('After select a image, paint the area where ' +
                'is replied')
        vbox_graph_replies.pack_start(Gtk.Label(help_text), False, False, padding=5)
        self._load_treemodel()
        self.show_all()
        self._modified_data = False
        self._selected_key = self.model.get_new_question_id()

    def __load_image_cb(self, button):
        try:
            chooser = ObjectChooser(_('Choose image'),
                self._activity, Gtk.DialogFlags.MODAL |
                Gtk.DialogFlags.DESTROY_WITH_PARENT, what_filter='Image')
        except:
            chooser = ObjectChooser(_('Choose image'),
                self._activity, Gtk.DialogFlags.MODAL |
                Gtk.DialogFlags.DESTROY_WITH_PARENT)
        try:
            result = chooser.run()
            if result == Gtk.ResponseType.ACCEPT:
                logging.debug('ObjectChooser: %r',
                        chooser.get_selected_object())
                jobject = chooser.get_selected_object()
                if jobject and jobject.file_path:
                    self.__load_image(jobject.file_path)
        finally:
            chooser.destroy()
            del chooser

    def __load_image(self, file_path):
        if self.draw_reply_area is not None:
            self.scrollwin.remove(self.scrollwin.get_children()[0])
            self.draw_reply_area = None
        self.draw_reply_area = DrawReplyArea(file_path, edit=True)
        self.scrollwin.add_with_viewport(self.draw_reply_area)
        # copy to resources directory
        self.model.check_resources_directory()
        resource_path = os.path.join(activity.get_activity_root(),
                'instance', 'resources')
        if not file_path.startswith(resource_path):
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
            self.treemodel.append([question['question'],
                    question['id_question']])

    def __add_reply_cb(self, button):
        self._add_reply_entry(reply_ok=len(self.replies_entries) == 0)

    def _add_reply_entry(self, reply_ok=True, text=None):
        hbox_row = Gtk.HBox()
        reply_entry = Gtk.Entry()
        if text is not None:
            reply_entry.set_text(text)
        reply_entry.connect('changed', self.__information_changed_cb)
        hbox_row.pack_start(reply_entry, True, True, padding=5)
        self.vbox_edit.pack_start(hbox_row, False, False, padding=5)
        if reply_ok:
            icon = Icon(icon_name='dialog-ok')
        else:
            icon = Icon(icon_name='dialog-cancel')

        hbox_row.pack_start(icon, False, False, padding=5)
        hbox_row.show_all()
        self.replies_entries.append(reply_entry)
        self.vbox_edit.replies.append(hbox_row)

    def select_question(self, treeview):
        if treeview.get_selection is None:
            return
        treestore, coldex = treeview.get_selection().get_selected()
        if coldex is None:
            return
        logging.debug('selected question %s', treestore.get_value(coldex, 1))
        if self._modified_data:
            # update data
            self._update_model(self._selected_key)
        self._selected_key = treestore.get_value(coldex, 1)
        self._display_model(self._selected_key)

    def _update_model(self, key):
        question = self.model.get_question(key)
        new_entry = False
        if question == None:
            question = {}
            new_entry = True
        replies = []

        question_type = self.questions_types[self.notebook.get_current_page()]

        question = {'question': self.question_entry.get_text(),
                    'type': question_type,
                    'id_question': key}

        if question_type == self.model.QUESTION_TYPE_TEXT:
            for reply_entry in self.replies_entries:
                if reply_entry.get_text() != '':
                    reply = {}
                    reply['text'] = reply_entry.get_text()
                    # The first is the valid
                    reply['valid'] = len(replies) == 0
                    replies.append(reply)
            question['replies'] = replies

        if question_type == self.model.QUESTION_TYPE_GRAPHIC:
            question['file_image'] = self._image_resource_path
            # save painted image
            resource_path = os.path.join(activity.get_activity_root(),
                    'instance', 'resources')
            reply_file_name = os.path.join(resource_path,
                    'reply_image_%s.png' % key)
            self.draw_reply_area.write_reply_png(reply_file_name)
            question['file_image_reply'] = reply_file_name

        if new_entry:
            self.model.data['questions'].append(question)
            self.treemodel.append([self.question_entry.get_text(), key])
        self._modified_data = False

    def _display_model(self, key):
        question = self.model.get_question(key)
        self._display_question(question)

    def _display_question(self, question, display_empty_entries=False):
        self.question_entry.set_text(question['question'])
        # remove old replies entries
        for hbox in self.vbox_edit.replies:
            self.vbox_edit.remove(hbox)
        self.vbox_edit.replies = []
        question_type = question['type']
        if question_type == self.model.QUESTION_TYPE_TEXT:
            self.notebook.set_current_page(0)
            # add replies
            for reply in question['replies']:
                if display_empty_entries or reply['text'] != '':
                    self._add_reply_entry(reply_ok=reply['valid'],
                            text=reply['text'])

        if question_type == self.model.QUESTION_TYPE_GRAPHIC:
            self.notebook.set_current_page(1)
            # show graph
            self.__load_image(question['file_image'])
            self.draw_reply_area.read_reply_png(question['file_image_reply'])
        self._modified_data = False

    def del_question(self):
        logging.debug('del question')
        if self._selected_key is not None:
            logging.debug('select key %s', self._selected_key)
            self.model.data['questions'].remove(self.model.get_question(
                                                        self._selected_key))
            self.treemodel.remove(
                        self.quest_listview.get_selection())
            self._modified_data = False
            self._selected_key = None
            self.emit('question_updated')

    def add_question(self):
        if self._modified_data:
            # update data
            self._update_model(self._selected_key)

        self._selected_key = self.model.get_new_question_id()

        question = {'question': '',
                    'type': self.model.QUESTION_TYPE_TEXT,
                    'replies': [{'text':'', 'valid':True},
                                {'text':'', 'valid':False}]}

        self._display_question(question, display_empty_entries=True)
        self.emit('question_updated')

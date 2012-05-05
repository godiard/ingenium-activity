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

from gettext import gettext as _
import os
import random
import logging

import gobject
import gtk
import webkit

from sugar.graphics import style
from sugar.graphics.toolbutton import ToolButton
from sugar.graphics.icon import Icon

import questions


class _DialogWindow(gtk.Window):

    # A base class for a modal dialog window.

    def __init__(self, icon_name, title):
        super(_DialogWindow, self).__init__()

        self.set_border_width(style.LINE_WIDTH)
        offset = style.GRID_CELL_SIZE
        width = gtk.gdk.screen_width() - style.GRID_CELL_SIZE * 2
        height = gtk.gdk.screen_height() - style.GRID_CELL_SIZE * 2
        self.set_size_request(width, height)
        self.set_position(gtk.WIN_POS_CENTER_ALWAYS)
        self.set_decorated(False)
        self.set_resizable(False)
        self.set_modal(True)

        vbox = gtk.VBox()
        self.add(vbox)

        toolbar = _DialogToolbar(icon_name, title)
        toolbar.connect('stop-clicked', self._stop_clicked_cb)
        vbox.pack_start(toolbar, False)

        self.content_vbox = gtk.VBox()
        self.content_vbox.set_border_width(style.DEFAULT_SPACING)
        vbox.add(self.content_vbox)

        self.connect('realize', self._realize_cb)

    def _stop_clicked_cb(self, source):
        self.destroy()

    def _realize_cb(self, source):
        self.window.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DIALOG)
        self.window.set_accept_focus(True)


class _DialogToolbar(gtk.Toolbar):

    # Displays a dialog window's toolbar, with title, icon, and close box.

    __gsignals__ = {
        'stop-clicked': (gobject.SIGNAL_RUN_LAST, None, ()),
    }

    def __init__(self, icon_name, title):
        super(_DialogToolbar, self).__init__()

        if icon_name is not None:
            icon = Icon()
            icon.set_from_icon_name(icon_name, gtk.ICON_SIZE_LARGE_TOOLBAR)
            self._add_widget(icon)

        self._add_separator()

        label = gtk.Label(title)
        self._add_widget(label)

        self._add_separator(expand=True)

        stop = ToolButton(icon_name='dialog-cancel')
        stop.set_tooltip(_('Done'))
        stop.connect('clicked', self._stop_clicked_cb)
        self.add(stop)

    def _add_separator(self, expand=False):
        separator = gtk.SeparatorToolItem()
        separator.set_expand(expand)
        separator.set_draw(False)
        self.add(separator)

    def _add_widget(self, widget):
        tool_item = gtk.ToolItem()
        tool_item.add(widget)
        self.add(tool_item)

    def _stop_clicked_cb(self, button):
        self.emit('stop-clicked')


class ResourceDialog(_DialogWindow):

    __gtype_name__ = 'ResourceDialog'

    def __init__(self, model, id_resource):
        resource = model.get_resource(id_resource)

        super(ResourceDialog, self).__init__(None, resource['title'])

        scrollwin = gtk.ScrolledWindow()
        scrollwin.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        self.content_vbox.pack_start(scrollwin)
        vbox = gtk.VBox()
        scrollwin.add_with_viewport(vbox)

        image = gtk.Image()
        vbox.pack_start(image, False, padding=5)
        image.set_from_file(resource['file_image'])

        editor = webkit.WebView()
        editor.set_editable(False)
        height = int(gtk.gdk.screen_height() / 3)
        editor.set_size_request(-1, height)
        vbox.pack_start(editor, False, padding=5)

        if resource['file_text'] != '':
            if os.path.exists(resource['file_text']):
                with open(resource['file_text'], 'r') as html_file:
                    editor.load_html_string(html_file.read(), 'file:///')


class QuestionDialog(_DialogWindow):

    __gtype_name__ = 'QuestionDialog'

    __gsignals__ = {
        'reply-selected': (gobject.SIGNAL_RUN_LAST, None,
                ([gobject.TYPE_STRING, gobject.TYPE_BOOLEAN])),
    }

    def __init__(self, model, id_question):
        self._id_question = id_question
        question = model.get_question(id_question)
        super(QuestionDialog, self).__init__(None, question['question'])

        scrollwin = gtk.ScrolledWindow()
        scrollwin.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        vbox = gtk.VBox()
        scrollwin.add_with_viewport(vbox)

        self.notebook = gtk.Notebook()
        self.notebook.set_show_tabs(False)
        # add a page with the controls to reply the question
        self.notebook.append_page(scrollwin)
        # ... and another to show the smiley according to the result
        self.image_result = gtk.Image()
        self.notebook.append_page(self.image_result)

        self.content_vbox.pack_start(self.notebook, True, True)

        question_type = question['type']

        if question_type == model.QUESTION_TYPE_TEXT:
            replies = []
            replies.extend(question['replies'])
            random.shuffle(replies)
            for reply in replies:
                hbox_row = gtk.HBox()
                reply_label = gtk.Label(reply['text'])
                hbox_row.pack_start(reply_label, True, padding=5)
                vbox.pack_start(hbox_row, False, padding=5)
                reply_button = gtk.Button(_('Select'))
                reply_button.connect('clicked', self.__button_reply_click_cb,
                        reply['valid'])
                hbox_row.pack_start(reply_button, False, padding=5)
                hbox_row.show_all()

        if question_type == model.QUESTION_TYPE_GRAPHIC:
            image_path = question['file_image']
            reply_image_path = question['file_image_reply']

            self.draw_reply_area = questions.DrawReplyArea(image_path,
                    reply_file_name=reply_image_path)
            vbox.pack_start(self.draw_reply_area, False, padding=5)
            self.draw_reply_area.connect('reply-selected',
                    self.__draw_reply_click_cb)

    def __button_reply_click_cb(self, widget, valid_reply):
        self._show_reply_feedback(valid_reply)

    def __draw_reply_click_cb(self, widget, valid_reply):
        self._show_reply_feedback(valid_reply)

    def _change_page(self):
        self.notebook.set_current_page(1)
        self.window.set_cursor(None)
        # wait 3 seconds
        #report and close
        gobject.timeout_add_seconds(3, self._close_all)

    def _close_all(self):
        self.destroy()

    def _show_reply_feedback(self, valid_reply):
        # load smiley image
        self.window.set_cursor(gtk.gdk.Cursor(gtk.gdk.WATCH))
        if valid_reply:
            smiley = random.choice(questions.SMILIES_OK)
        else:
            smiley = random.choice(questions.SMILIES_WRONG)
        image_file_name = './images/smilies/%s.svg' % smiley
        size = gtk.gdk.screen_height() / 2
        pixbuf = gtk.gdk.pixbuf_new_from_file_at_size(image_file_name, size,
                size)
        self.image_result.set_from_pixbuf(pixbuf)
        # report result
        self.emit('reply-selected', self._id_question, valid_reply)

        # wait one second and change the page
        gobject.timeout_add_seconds(1, self._change_page)

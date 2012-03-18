import gtk
import gobject
import webkit
import logging
import os
import shutil

from gettext import gettext as _

from gobject import SIGNAL_RUN_FIRST

from sugar.activity import activity
from sugar.graphics.icon import Icon
from sugar.graphics.objectchooser import ObjectChooser


class CollectResourcesWin(gtk.HBox):

    __gsignals__ = {
        'resource_updated': (SIGNAL_RUN_FIRST, None, [])
    }

    def __init__(self, activity):
        self._activity = activity
        gtk.HBox.__init__(self)
        self.model = activity.model
        """
        +---------+------------------------------+
        |Listview | Title   [                  ] |
        |         +------------------------------+
        |         | +--------------+ Size        |
        |         | | ImageView    | Load from   |
        |         | |              | Journal     |
        |         | |              | Show as     |
        |         | +--------------+ |IconView | |
        |         | +--------------------------+ |
        |         | | Text                     | |
        |         | +--------------------------+ |
        +---------+------------------------------+
        """
        # Listview
        self.resource_listview = gtk.TreeView()
        width = int(gtk.gdk.screen_width() / 3)
        self.resource_listview.set_size_request(width, -1)

        self.resource_listview.connect('cursor-changed', self.select_resource)

        # title and id_resource
        self.treemodel = gtk.ListStore(gobject.TYPE_STRING,
                gobject.TYPE_STRING)
        self.resource_listview.set_model(self.treemodel)
        renderer = gtk.CellRendererText()
        renderer.set_property('wrap-mode', gtk.WRAP_WORD)
        self.treecol = gtk.TreeViewColumn(_('Resources'), renderer, text=0)
        self.resource_listview.append_column(self.treecol)
        self.tree_scroller = gtk.ScrolledWindow(hadjustment=None,
                vadjustment=None)
        self.tree_scroller.set_policy(gtk.POLICY_NEVER,
                gtk.POLICY_AUTOMATIC)
        self.tree_scroller.add(self.resource_listview)
        self.pack_start(self.tree_scroller, False)

        vbox = gtk.VBox()
        self.pack_start(vbox, True)

        hbox_title = gtk.HBox()
        hbox_title.pack_start(gtk.Label(_('Title')), False, padding=5)
        self.title_entry = gtk.Entry()
        self.title_entry.connect('changed', self.__information_changed_cb)
        hbox_title.pack_start(self.title_entry, True, padding=5)
        vbox.pack_start(hbox_title, False, padding=5)

        hbox_image = gtk.HBox()
        scrollwin = gtk.ScrolledWindow()
        scrollwin.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.image = gtk.Image()
        scrollwin.add_with_viewport(self.image)
        hbox_image.pack_start(scrollwin, True, padding=5)
        vbox_image = gtk.VBox()
        self.load_image_button = gtk.Button(_('Load Image'))
        self.load_image_button.connect('clicked', self.__load_image_cb)
        vbox_image.pack_start(self.load_image_button, False, padding=5)

        size_label = gtk.Label(_('Image size:'))
        vbox_image.pack_start(size_label, False, padding=5)
        self.size_label_value = gtk.Label('')
        vbox_image.pack_start(self.size_label_value, False, padding=5)
        hbox_image.pack_start(vbox_image, False, padding=5)
        vbox.pack_start(hbox_image, True, padding=5)

        # show as icon
        self.show_as_icon_check = gtk.CheckButton()
        self._set_show_as_icon_label()
        self.show_as_icon_check.connect('toggled', self.__show_as_toggled_cb)
        vbox_image.pack_start(self.show_as_icon_check, False, padding=5)

        self._icons_store = gtk.ListStore(str, gtk.gdk.Pixbuf, str)
        self._icons_store.set_sort_column_id(0, gtk.SORT_ASCENDING)
        self._iconview = gtk.IconView(self._icons_store)
        self._iconview.set_text_column(0)
        self._iconview.set_pixbuf_column(1)
        self._iconview.set_sensitive(False)
        self._iconview.set_selection_mode(gtk.SELECTION_SINGLE)
        self.load_icons()
        self._iconview.connect('item-activated', self.__iconview_activated_cb)
        scrolled = gtk.ScrolledWindow()
        scrolled.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        scrolled.add_with_viewport(self._iconview)

        vbox_image.pack_start(scrolled, True, padding=5)

        #hbox_editor = gtk.HBox()
        self.editor = webkit.WebView()
        self.title_entry.connect('changed',
                self.__information_changed_cb)
        self.editor.set_editable(True)
        height = int(gtk.gdk.screen_height() / 3)
        self.editor.set_size_request(-1, height)
        #hbox_editor.pack_start(self.editor, False, padding=5)
        vbox.pack_start(self.editor, False, padding=5)

        self._load_treemodel()
        self.show_all()
        self._modified_data = False
        self._selected_key = self.model.get_new_resource_id()

        self._image_resource_path = None

    def __show_as_toggled_cb(self, button):
        self._iconview.set_sensitive(button.get_active())
        if not button.get_active():
            self._set_show_as_icon_label()
        self._modified_data = True

    def __iconview_activated_cb(self, widget, item):
        model = widget.get_model()
        image_file_name = model[item][2]
        self._set_show_as_icon_label(self._get_image_name(image_file_name))

    def _get_image_name(self, image_file_name):
        image_name = image_file_name[image_file_name.rfind('/') + 1:]
        return image_name[:image_name.find('.')]

    def _set_show_as_icon_label(self, text=None):
        if text is None:
            self.show_as_icon_check.set_label(_('Show as Icon:'))
        else:
            self.show_as_icon_check.set_label(_('Show as %s') % text)

    def load_icons(self):
        images_path = os.path.join(activity.get_bundle_path(),
                'images/resource_icons')
        logging.error('Loading resource icons from %s', images_path)
        for file_name in os.listdir(images_path):
            if not file_name.endswith('.txt'):
                image_file_name = os.path.join(images_path, file_name)
                logging.error('Adding %s', image_file_name)
                pxb = gtk.gdk.pixbuf_new_from_file_at_size(image_file_name,
                        100, 100)
                self._icons_store.append(['', pxb, image_file_name])

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
        self.image.set_from_file(file_path)
        width = self.image.props.pixbuf.get_width()
        height = self.image.props.pixbuf.get_height()
        self.size_label_value.set_text('%s x %s px' % (width, height))
        # copy to resources directory
        self.model.check_resources_directory()
        resource_path = os.path.join(activity.get_activity_root(),
                'instance', 'resources')
        shutil.copy(file_path, resource_path)
        self._image_resource_path = os.path.join(resource_path,
                os.path.basename(file_path))
        self._modified_data = True

    def __information_changed_cb(self, entry):
        self._modified_data = True

    def _load_treemodel(self):
        logging.error('loading treemodel')
        for resource in self.model.data['resources']:
            logging.error('adding resource %s', resource)
            self.treemodel.append([resource['title'], resource['id_resource']])

    def select_resource(self, treeview):
        treestore, coldex = treeview.get_selection().get_selected()
        logging.debug('selected resource %s', treestore.get_value(coldex, 1))
        if self._modified_data:
            # update data
            self._update_model(self._selected_key)
        self._selected_key = treestore.get_value(coldex, 1)
        self._display_model(self._selected_key)

    def _update_model(self, key):
        resource = self.model.get_resource(key)
        new_entry = False
        if resource == None:
            resource = {}
            new_entry = True
        # save text with the same name as the image and extension .html
        with open(self._image_resource_path + '.html', 'w') as html_file:
            html_file.write(self._get_html())

        # show_as
        show_as = None
        if self.show_as_icon_check.get_active():
            item = self._iconview.get_selected_items()[0][0]
            show_as = self._icons_store[item][2]

        resource = {'title': self.title_entry.get_text(),
                    'file_image': self._image_resource_path,
                    'file_text': self._image_resource_path + '.html',
                    'show_as': show_as,
                    'id_resource': key}

        if new_entry:
            self.model.data['resources'].append(resource)
            self.treemodel.append([self.title_entry.get_text(), key])

        self._modified_data = False

    def _get_html(self):
        script = 'document.title=document.documentElement.innerHTML;'
        self.editor.execute_script(script)
        return self.editor.get_main_frame().get_title()

    def _display_model(self, key):
        resource = self.model.get_resource(key)
        self._display_resource(resource)

    def _display_resource(self, resource):
        self.title_entry.set_text(resource['title'])
        if resource['file_text'] != '':
            if os.path.exists(resource['file_text']):
                with open(resource['file_text'], 'r') as html_file:
                    self.editor.load_html_string(html_file.read(), 'file:///')
        else:
            self.editor.load_html_string('', 'file:///')

        if resource['file_image'] != '':
            if os.path.exists(resource['file_image']):
                self.image.set_from_file(resource['file_image'])
                self._image_resource_path = resource['file_image']
        else:
            self.image.clear()
            self._image_resource_path = None

        # show as
        self.show_as_icon_check.set_active(resource['show_as'] is not None)
        self._iconview.set_sensitive(self.show_as_icon_check.get_active())
        self._set_show_as_icon_label(self._get_image_name(resource['show_as']))

        self._modified_data = False

    def del_resource(self):
        logging.debug('del resource')
        # TODO
        if self._selected_key is not None:
            logging.debug('select key %s', self._selected_key)
            model, tree_iter = \
                    self.resource_listview.get_selection().get_selected()
            model.remove(tree_iter)
            self.model.data['resources'].remove(self.model.get_resource(
                                                        self._selected_key))
            self._modified_data = False
            self._selected_key = None
            self.emit('resource_updated')

    def add_resource(self):
        if self._modified_data:
            # update data
            self._update_model(self._selected_key)

        self._selected_key = self.model.get_new_resource_id()
        resource = {'title': '',
                    'file_image': '',
                    'file_text': '',
                    'show_as': None,
                    'id_resource': self._selected_key}
        self._display_resource(resource)
        self.emit('resource_updated')

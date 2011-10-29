import gtk
import gobject
import webkit
import logging

from gettext import gettext as _
from sugar.graphics.icon import Icon


class CollectResourcesWin(gtk.HBox):

    def __init__(self, model):
        gtk.HBox.__init__(self)
        self.model = model
        """
        +---------+------------------------------+
        |Listview | Title   [                  ] |
        |         +------------------------------+
        |         | +--------------+ Size        |
        |         | | ImageView    | Load from   |
        |         | +--------------+ Journal     |
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
        self.treemodel = gtk.ListStore(gobject.TYPE_STRING)
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
        self.image = gtk.Image()
        hbox_image.pack_start(self.image, True, padding=5)
        vbox_image = gtk.VBox()
        self.load_image_button = gtk.Button('Load Image')
        vbox_image.pack_start(self.load_image_button, False, padding=5)
        self.size_label = gtk.Label('Image size:')
        vbox_image.pack_start(self.size_label, False, padding=5)
        hbox_image.pack_start(vbox_image, False, padding=5)
        vbox.pack_start(hbox_image, True, padding=5)

        #hbox_editor = gtk.HBox()
        self.editor = webkit.WebView()
        self.editor.set_editable(True)
        height = int(gtk.gdk.screen_height() / 3)
        self.editor.set_size_request(-1, height)
        #hbox_editor.pack_start(self.editor, False, padding=5)
        vbox.pack_start(self.editor, False, padding=5)

        self._load_treemodel()
        self.show_all()
        self._modified_data = False
        self._selected_key = None

    def __information_changed_cb(self, entry):
        logging.debug('Data modified')
        self._modified_data = True

    def _load_treemodel(self):
        logging.error('loading treemodel')
        for resource in self.model.data['resources']:
            logging.error('adding resource %s', resource)
            self.treemodel.append([resource['title']])

    def select_resource(self, treeview):
        treestore, coldex = treeview.get_selection().get_selected()
        logging.debug('selected resource %s', treestore.get_value(coldex, 0))
        if self._modified_data:
            # update data
            self._update_model(self._selected_key)
        self._selected_key = treestore.get_value(coldex, 0)
        self._display_model(self._selected_key)

    def _update_model(self, key):
        resource = self._get_resource(key)
        new_entry = False
        if resource == None:
            resource = {}
            new_entry = True
        # TODO
        resource = {'title': self.title_entry.get_text(),
                    'file_image': '',
                    'file_text': ''}
        if new_entry:
            self.model.data['resources'].append(resource)
            self.treemodel.append([self.title_entry.get_text()])
        self._modified_data = False

    def _display_model(self, key):
        resource = self._get_resource(key)
        self._display_resource(resource)

    def _display_resource(self, resource):
        self.title_entry.set_text(resource['title'])
        # TODO
        self._modified_data = False

    def _get_resource(self, key):
        for resource in self.model.data['resources']:
            if resource['title'] == key:
                return resource
        return None

    def del_resource(self):
        logging.debug('del resource')
        # TODO
        if self._selected_key is not None:
            logging.debug('select key %s', self._selected_key)
            self.model.data['resources'].remove(self._get_question(
                                                        self._selected_key))
            self.treemodel.remove(
                        self.resource_listview.get_selection())
            self._modified_data = False
            self._selected_key = None

    def add_resource(self):
        if self._modified_data:
            # update data
            self._update_model(self._selected_key)

        self._selected_key = None
        resource = {'title': '',
                    'file_image': '',
                    'file_text': ''}
        self._display_resource(resource)
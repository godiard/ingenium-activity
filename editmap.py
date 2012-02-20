from gettext import gettext as _
import logging
import os

import gtk

from sugar.activity import activity

from game_map import GameMap
from mapview import TopMapView
from mapnav import MapNavView


class EditMapWin(gtk.HBox):

    def __init__(self, model):
        gtk.HBox.__init__(self)
        self.model = model

        if not 'map_data' in self.model.data or \
                self.model.data['map_data'] is None:
            self.game_map = GameMap()
        else:
            self.game_map = GameMap(self.model.data['map_data'])

        self.model.data['map_data'] = self.game_map.data

        self.nav_view = MapNavView(self.game_map)
        self.top_view = TopMapView(self.game_map, 150, 150)
        self.top_view.show_position(self.nav_view.x, self.nav_view.y,
                self.nav_view.direction)
        self.nav_view.connect('position-changed', self.show_position,
                self.top_view)
        self.pack_start(self.nav_view, True, True)
        rigth_vbox = gtk.VBox()
        rigth_vbox.pack_start(self.top_view, False, False)
        notebook = gtk.Notebook()
        rigth_vbox.pack_start(notebook, False, False)

        # resources
        self._resources_store = gtk.ListStore(str, gtk.gdk.Pixbuf)
        self._resources_store.set_sort_column_id(0, gtk.SORT_ASCENDING)
        resources_iconview = gtk.IconView(self._resources_store)
        resources_iconview.set_text_column(0)
        resources_iconview.set_pixbuf_column(1)
        self.load_resources()

        # furniture
        self._furniture_store = gtk.ListStore(str, gtk.gdk.Pixbuf)
        self._furniture_store.set_sort_column_id(0, gtk.SORT_ASCENDING)
        furniture_iconview = gtk.IconView(self._furniture_store)
        furniture_iconview.set_text_column(0)
        furniture_iconview.set_pixbuf_column(1)
        self.load_furniture()

        notebook.append_page(resources_iconview, gtk.Label(_('Resources')))
        notebook.append_page(furniture_iconview, gtk.Label(_('Furniture')))

        self.pack_start(rigth_vbox, False, False)
        self.nav_view.grab_focus()
        self.show_all()

    def show_position(self, nav_view, x, y, direction, top_view):
        self.top_view.show_position(x, y, direction)

    def load_resources(self):
        logging.error('Loading resources')
        for resource in self.model.data['resources']:
            title = resource['title']
            file_image = resource['file_image']
            logging.error('Adding %s %s', title, file_image)
            pxb = gtk.gdk.pixbuf_new_from_file_at_size(file_image, 100, 100)
            self._resources_store.append([title, pxb])

    def load_furniture(self):
        images_path = os.path.join(activity.get_bundle_path(),
                'images/furniture')
        logging.error('Loading furniture from %s', images_path)
        for file_name in os.listdir(images_path):
            if not file_name.endswith('.txt'):
                image_file_name = os.path.join(images_path, file_name)
                logging.error('Adding %s', image_file_name)
                pxb = gtk.gdk.pixbuf_new_from_file_at_size(image_file_name,
                        100, 100)
                self._furniture_store.append(['', pxb])

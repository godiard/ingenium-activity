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

        left_vbox = gtk.VBox()
        self.nav_view = MapNavView(self.game_map, mode=MapNavView.MODE_EDIT)
        self.top_view = TopMapView(self.game_map, 150, 150)
        self.top_view.show_position(self.nav_view.x, self.nav_view.y,
                self.nav_view.direction)
        self.nav_view.connect('position-changed', self.show_position,
                self.top_view)

        name_box = gtk.HBox()
        name_box.pack_start(gtk.Label(_('Room name')), False, False, padding=5)
        self.room_name_entry = gtk.Entry()
        self.room_name_entry.connect('focus-in-event', self.__room_name_in_cb)
        self.room_name_entry.connect('focus-out-event',
                self.__room_name_out_cb)
        self._room_name = ''

        name_box.pack_start(self.room_name_entry, True, True, padding=5)

        left_vbox.pack_start(name_box, False, False, padding=5)
        left_vbox.pack_start(self.nav_view, True, True)

        self.pack_start(left_vbox, True, True)
        rigth_vbox = gtk.VBox()
        rigth_vbox.pack_start(self.top_view, False, False)
        notebook = gtk.Notebook()
        rigth_vbox.pack_start(notebook, True, True)

        # resources
        # store: title, pxb, image_file_name, id_resource/id_question, type
        # type: question or resource
        self._resources_store = gtk.ListStore(str, gtk.gdk.Pixbuf, str, str,
                str)
        self._resources_store.set_sort_column_id(0, gtk.SORT_ASCENDING)
        self.resources_iconview = gtk.IconView(self._resources_store)
        self.resources_iconview.set_text_column(0)
        self.resources_iconview.set_pixbuf_column(1)
        self.load_resources_and_questions()
        self.resources_iconview.connect('item-activated',
                self.__resource_iconview_activated_cb)

        # furniture
        self._furniture_store = gtk.ListStore(str, gtk.gdk.Pixbuf, str)
        self._furniture_store.set_sort_column_id(0, gtk.SORT_ASCENDING)
        self.furniture_iconview = gtk.IconView(self._furniture_store)
        self.furniture_iconview.set_text_column(0)
        self.furniture_iconview.set_pixbuf_column(1)
        self.load_furniture()
        self.furniture_iconview.connect('item-activated',
                self.__iconview_activated_cb)

        scrolled1 = gtk.ScrolledWindow()
        scrolled1.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        scrolled1.add_with_viewport(self.resources_iconview)
        notebook.append_page(scrolled1, gtk.Label(_('Resources & ?')))
        scrolled2 = gtk.ScrolledWindow()
        scrolled2.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        scrolled2.add_with_viewport(self.furniture_iconview)
        notebook.append_page(scrolled2, gtk.Label(_('Furniture')))

        self.pack_start(rigth_vbox, False, False)
        self.nav_view.grab_focus()

        # init room name
        room_key = self.game_map.get_room(self.nav_view.x, self.nav_view.y)
        self.room_name = self.game_map.get_room_name(room_key)
        self.room_name_entry.set_text(self.room_name)

        self.show_all()

    def __room_name_in_cb(self, widget, event):
        self.room_name = widget.get_text()

    def __room_name_out_cb(self, widget, event):
        if widget.get_text() != self.room_name:
            # TODO: save the name in the model
            room_key = self.game_map.get_room(self.nav_view.x, self.nav_view.y)
            self.game_map.set_room_name(room_key, widget.get_text())

    def show_position(self, nav_view, x, y, direction, top_view):
        self.top_view.show_position(x, y, direction)
        room_key = self.game_map.get_room(self.nav_view.x, self.nav_view.y)
        room_name = self.game_map.get_room_name(room_key)
        self.room_name_entry.set_text(room_name)

    def load_resources_and_questions(self, origin=None):
        logging.error('Loading resources')
        self._resources_store.clear()
        for resource in self.model.data['resources']:
            title = resource['title']
            if resource['show_as'] is None:
                image_file_name = resource['file_image']
            else:
                image_file_name = resource['show_as']

            id_resource = resource['id_resource']
            logging.error('Adding %s %s %s', title, image_file_name,
                    id_resource)
            pxb = gtk.gdk.pixbuf_new_from_file_at_size(image_file_name, 100,
                    100)
            self._resources_store.append([title, pxb, image_file_name,
                    id_resource, 'resource'])
        logging.error('Loading questions')
        for question in self.model.data['questions']:
            text = question['question']
            if question['type'] == self.model.QUESTION_TYPE_GRAPHIC:
                image_file_name = question['file_image']
            else:
                image_file_name = './icons/question.svg'

            id_question = question['id_question']
            logging.error('Adding %s %s %s', text, image_file_name,
                    id_question)
            pxb = gtk.gdk.pixbuf_new_from_file_at_size(image_file_name, 100,
                    100)
            self._resources_store.append([text, pxb, image_file_name,
                    id_question, 'question'])

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
                self._furniture_store.append(['', pxb, image_file_name])

    def __iconview_activated_cb(self, widget, item):
        model = widget.get_model()
        image_file_name = model[item][2]
        self._add_image(image_file_name)

    def __resource_iconview_activated_cb(self, widget, item):
        model = widget.get_model()
        image_file_name = model[item][2]
        id_object = model[item][3]
        type_object = model[item][4]
        self._add_image(image_file_name, id_object, type_object)

    def _add_image(self, image_file_name, id_object=None, type_object=None):
        logging.error('Image %s selected', image_file_name)
        x = self.nav_view.x
        y = self.nav_view.y
        direction = self.nav_view.direction
        wall_object = {'image_file_name': image_file_name,
                'wall_x': 50.0, 'wall_y': 50.0, 'wall_scale': 0.2}
        if id_object is not None:
            wall_object['id_object'] = id_object
        if type_object is not None:
            wall_object['type_object'] = type_object
        self.game_map.add_object_to_wall(x, y, direction, wall_object)
        self.nav_view.update_wall_info(x, y, direction)
        self.nav_view.grab_focus()

    def add_selected_object(self):
        if self.furniture_iconview.is_focus():
            item = self.furniture_iconview.get_selected_items()[0][0]
            image_file_name = self._furniture_store[item][2]
            self._add_image(image_file_name)
        if self.resources_iconview.is_focus():
            item = self.resources_iconview.get_selected_items()[0][0]
            image_file_name = self._resources_store[item][2]
            id_object = self._resources_store[item][3]
            type_object = self._resources_store[item][4]
            self._add_image(image_file_name, id_object, type_object)

    def remove_selected_object(self):
        self.nav_view.remove_selected_object()
        self.nav_view.grab_focus()

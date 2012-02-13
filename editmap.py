import gtk

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
        self.pack_start(self.top_view, False, False)
        self.nav_view.grab_focus()
        self.show_all()

    def show_position(self, nav_view, x, y, direction, top_view):
        self.top_view.show_position(x, y, direction)

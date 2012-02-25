"""
This is a data structure to define a game map
At start we will use only one map, but later we wil add more maps
"""

"""
Default Map

The symbol # is a door.

       0     1     2     3
    +-----+-----+-----+-----+
 0  |           A           |
    |                       |
    +--#--+--#--------+--#--+
 1  |     |     C     #     |
    |     #           |     |
    +  B  +-----------+  E  +
 2  |     |     D     |     |
    |     #           |     |
    +--#--+-----------+-----+
 3  |     |     G     |     |
    |     #           |     |
    +  F  +-----------+  I  +
 4  |     #     H     #     |
    |     |           |     |
    +--#--+--#--------+--#--+
 5  |           J           |
    |                       |
    +-----+-----+-----+-----+

We represent this map with the following structure:
"""


class GameMap():

    default_data = {'max_x': 4, 'max_y': 6,

        'rooms': {'A': {'wall_color': (0.7, 0.8, 0.7)},
                'B': {'wall_color': (0.8, 0.8, 0.6)},
                'C': {'wall_color': (0.6, 0.6, 1)},
                'D': {'wall_color': (0.7, 0.8, 0.7)},
                'E': {'wall_color': (0.8, 0.8, 0.6)},
                'F': {'wall_color': (0.7, 0.8, 0.7)},
                'G': {'wall_color': (0.3, 0.4, 0.3)},
                'H': {'wall_color': (0.8, 0.8, 0.6)},
                'I': {'wall_color': (0.7, 0.8, 0.7)},
                'J': {'wall_color': (0.8, 0.8, 0.6)}},

        'cells': ['AAAA',
                  'BCCE',
                  'BDDE',
                  'FGGI',
                  'FHHI',
                  'JJJJ'],

        # walls are defined by the cell position x,y and the direction
        # N,S,E,W
        'walls': [{'position': [0, 0, 'S'], 'doors': ['door_1']},
                    {'position': [1, 0, 'S'], 'doors': ['door_2']},
                    {'position': [3, 0, 'S'], 'doors': ['door_3']},
                    {'position': [0, 1, 'E'], 'doors': ['door_4']},
                    {'position': [2, 1, 'E'], 'doors': ['door_6']},
                    {'position': [0, 2, 'S'], 'doors': ['door_7']},
                    {'position': [0, 2, 'E'], 'doors': ['door_8']},
                    {'position': [4, 2, 'S'], 'doors': ['door_11']},
                    {'position': [0, 3, 'E'], 'doors': ['door_12']},
                    {'position': [3, 3, 'E'], 'doors': ['door_13']},
                    {'position': [0, 4, 'S'], 'doors': ['door_14']},
                    {'position': [0, 4, 'E'], 'doors': ['door_15']},
                    {'position': [1, 4, 'S'], 'doors': ['door_16']},
                    {'position': [2, 4, 'E'], 'doors': ['door_17']},
                    {'position': [3, 4, 'S'], 'doors': ['door_18']}]}

    def __init__(self, data=None):
        if data is None:
            self.data = self.default_data
        else:
            self.data = data

    def get_room(self, x, y):
        """ Return room key and the dictionary based in
            the position x,y in the map"""
        room_key = self.data['cells'][y][x]
        return room_key

    def set_room_name(self, room_key, room_name):
        self.data['rooms'][room_key]['room_name'] = room_name

    def get_room_name(self, room_key):
        if 'room_name' in self.data['rooms'][room_key]:
            return self.data['rooms'][room_key]['room_name']
        else:
            return ''

    def get_next_coords(self, x, y, direction):
        if direction == 'N':
            y -= 1
        if direction == 'S':
            y += 1
        if direction == 'W':
            x -= 1
        if direction == 'E':
            x += 1
        if x < 0 or y < 0 or \
            x > (self.data['max_x'] - 1) or \
            y > (self.data['max_y'] - 1):
            return -1, -1
        return x, y

    def get_next_room(self, x, y, direction):
        x, y = self.get_next_coords(x, y, direction)
        if x == -1 and y == -1:
            return None
        return self.get_room(x, y)

    def get_reversed_direction(self, direction):
        if direction == 'N':
            return 'S'
        if direction == 'S':
            return 'N'
        if direction == 'E':
            return 'W'
        if direction == 'W':
            return 'E'

    def get_direction_cw(self, direction):
        """Return the direction if the user turn clock wise"""
        if direction == 'N':
            return 'E'
        if direction == 'S':
            return 'W'
        if direction == 'E':
            return 'S'
        if direction == 'W':
            return 'N'

    def get_direction_ccw(self, direction):
        """Return the direction if the user turn reverse clock wise"""
        if direction == 'N':
            return 'W'
        if direction == 'S':
            return 'E'
        if direction == 'E':
            return 'N'
        if direction == 'W':
            return 'S'

    def get_wall_info(self, x, y, direction):
        """ Return the array of objects associated to a defined wall
            or None if there are not a wall in this cell and direction"""

        # verify if there are a wall in the requested position
        actual_room = self.get_room(x, y)
        next_room = self.get_next_room(x, y, direction)
        # if the two rooms are the same, there are no wall
        if next_room is not None and actual_room == next_room:
            return None
        # Search in walls data
        for wall in self.data['walls']:
            if wall['position'] == [x, y, direction]:
                if not 'objects' in wall:
                    wall['objects'] = []
                return wall['objects']
        return []

    def add_object_to_wall(self, x, y, direction, wall_object):
        """ Add a object to the array of objects associated to a defined wall
        """
        # verify if there are a wall in the requested position
        actual_room = self.get_room(x, y)
        next_room = self.get_next_room(x, y, direction)
        # if the two rooms are the same, there are no wall
        if next_room is not None and actual_room == next_room:
            return None
        # Search in walls data
        found = False
        for wall in self.data['walls']:
            if wall['position'] == [x, y, direction]:
                if not 'objects' in wall:
                    wall['objects'] = []
                wall['objects'].append(wall_object)
                found = True
        if not found:
            wall_info = {'position': [x, y, direction], 'objects': []}
            wall_info['objects'].append(wall_object)
            self.data['walls'].append(wall_info)

    def del_object_from_wall(self, x, y, direction, wall_object):
        for wall in self.data['walls']:
            if wall['position'] == [x, y, direction]:
                # locate the object:
                for order, existing_object in enumerate(wall['objects']):
                    if existing_object == wall_object:
                        del wall['objects'][order]
                        break

    def get_wall_color(self, x, y):
        room = self.get_room(x, y)
        return self.data['rooms'][room]['wall_color']

    def go_right(self, x, y, direction):
        """ Return next position if the user go to the right"""
        # check if there are a wall
        direction_cw = self.get_direction_cw(direction)
        wall_right = self.get_wall_info(x, y, direction_cw)
        if wall_right is not None:
            return x, y, direction_cw
        if direction == 'N':
            return x + 1, y, direction
        if direction == 'E':
            return x, y + 1, direction
        if direction == 'S':
            return x - 1, y, direction
        if direction == 'W':
            return x, y - 1, direction

    def go_left(self, x, y, direction):
        """ Return next position if the user go to the left"""
        # check if there are a wall
        direction_ccw = self.get_direction_ccw(direction)
        wall_left = self.get_wall_info(x, y, direction_ccw)
        if wall_left is not None:
            return x, y, direction_ccw
        if direction == 'N':
            return x - 1, y, direction
        if direction == 'E':
            return x, y - 1, direction
        if direction == 'S':
            return x + 1, y, direction
        if direction == 'W':
            return x, y + 1, direction

    def cross_door(self, x, y, direction):
        """ Return next position if the user go to the left"""
        # verify is the door is in the right position/direction
        if not self.have_door(x, y, direction):
            return x, y, direction
        else:
            new_x, new_y, new_dir = self.go_forward(x, y, direction)
            if self.get_wall_info(new_x, new_y, new_dir) is None:
                new_x, new_y, new_dir = self.go_forward(new_x, new_y,
                        new_dir)
            return new_x, new_y, new_dir

    def go_forward(self, x, y, direction):
        if direction == 'N':
            return x, y - 1, direction
        if direction == 'E':
            return x + 1, y, direction
        if direction == 'S':
            return x, y + 1, direction
        if direction == 'W':
            return x - 1, y, direction

    def have_door(self, x, y, direction):
        """ Return if the wall have a door
            or None if there are not a wall in this cell and direction"""

        # verify if there are a wall in the requested position
        actual_room = self.get_room(x, y)
        next_room = self.get_next_room(x, y, direction)
        # if the two rooms are the same, there are no wall
        if next_room is not None and actual_room == next_room:
            return None
        # Search in walls data
        for wall in self.data['walls']:
            if wall['position'] == [x, y, direction]:
                return 'doors' in wall and len(wall['doors']) > 0
        # look for information in the other side of the room too.
        # (only valid for doors)
        if next_room is not None:
            reversed_direction = self.get_reversed_direction(direction)
            x2, y2 = self.get_next_coords(x, y, direction)
            if x2 == -1 and y2 == -1:
                return []
            for wall in self.data['walls']:
                if wall['position'] == [x2, y2, reversed_direction]:
                    return 'doors' in wall and len(wall['doors']) > 0
        # Nothing found
        return False


# testing
if __name__ == '__main__':

    game_map = GameMap()
    print "test get_room"
    print game_map.get_room(0, 0)
    print game_map.get_room(3, 2)
    print game_map.get_room(1, 4)
    print game_map.get_room(3, 5)

    print "test get_next_room"
    print game_map.get_next_room(3, 5, 'N')
    print game_map.get_next_room(3, 3, 'W')
    print game_map.get_next_room(2, 1, 'S')

    print "test get_wall_info"
    print game_map.get_wall_info(0, 3, 'N')
    print game_map.get_wall_info(0, 3, 'E')
    print game_map.get_wall_info(0, 3, 'S')
    print game_map.get_wall_info(0, 3, 'W')

    print "test go_right"
    print game_map.go_right(1, 1, 'N')
    print game_map.go_right(2, 1, 'N')

    print "test go_left"
    print game_map.go_left(1, 1, 'N')
    print game_map.go_left(2, 1, 'N')

    print "test cross_door"
    print game_map.cross_door(1, 1, 'N')
    print game_map.cross_door(2, 1, 'N')

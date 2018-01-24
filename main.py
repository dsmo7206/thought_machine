#!/usr/bin/python3

import re
import sys
from collections import namedtuple

MovementTurn = namedtuple('MovementTurn', ['ship_x', 'ship_y', 'actions'])
ShootingTurn = namedtuple('ShootingTurn', ['target_x', 'target_y'])
Ship         = namedtuple('Ship',         ['x', 'y', 'direction', 'alive'])

# Exceptions - none of these should happen in an input file
# that obeys the rules of the game.

class InvalidTurn(Exception): pass
class InvalidTurnType(InvalidTurn): pass
class MoveOutsideBoard(InvalidTurn): pass
class MovingSunkShip(InvalidTurn): pass
class NoShipAtLocation(InvalidTurn): pass
class ShipAtMoveTarget(InvalidTurn): pass

# The different types of action (result) for a turn - for testing

MovedShip = namedtuple('MovedShip', ['start_x', 'start_y', 'start_direction', 'end_x', 'end_y', 'end_direction'])
ShotNoTarget = namedtuple('ShotNoTarget', ['target_x', 'target_y'])
SunkAliveShip = namedtuple('SunkAliveShip', ['ship_x', 'ship_y'])
SunkDeadShip = namedtuple('SunkDeadShip', ['ship_x', 'ship_y'])

# There are many ways to do this - we could store the directions 
# as (0, 1, 2, 3) and then increment/decrement (mod 4) for example,
# but this is reasonably clear and the performance won't be terrible.
# It's Python - everything (almost) is dicts anyway :)

DIRECTION_TRANSITIONS = {
    'N': {'L': 'W', 'R': 'E'},
    'S': {'L': 'E', 'R': 'W'},
    'E': {'L': 'N', 'R': 'S'},
    'W': {'L': 'S', 'R': 'N'}
}

DIRECTION_DELTAS = {
    'N': ( 0,  1),
    'S': ( 0, -1),
    'W': (-1,  0),
    'E': ( 1,  0)
}

class FileReader:

    # This may be overkill, but I figure that to be robust, and also in the sake of simplified code
    # I'm just going to use regexes to parse the lines. I can very easily allow flexible whitespace
    # with this approach.
    GRID_REGEX = re.compile(r'\(\s*(?P<x_coord>\d+)\s*,\s*(?P<y_coord>\d+)\s*,\s*(?P<direction>[NESW])\s*\)')
    TURN_REGEX = re.compile(r'\(\s*(?P<x_coord>\d+)\s*,\s*(?P<y_coord>\d+)\s*\)\s*(?P<actions>[LRM]*)')

    def __init__(self, filename):
        self.filename = filename
    
    def __enter__(self):
        self.file = open(self.filename, 'r')
        # Read initial state
        self.board_size = int(self.file.readline().strip())
        self.initial_ships = [
            Ship(int(match.group('x_coord')), int(match.group('y_coord')), match.group('direction'), True)
            for match in self.GRID_REGEX.finditer(self.file.readline().strip())
        ]
        return self

    def __exit__(self, *exc):
        self.file.close()
    
    @classmethod
    def make_turn_from_line(cls, line):
        match = cls.TURN_REGEX.search(line.strip())
        # Extract the values
        x_coord = int(match.group('x_coord'))
        y_coord = int(match.group('y_coord'))
        actions = match.group('actions')

        if actions:
            return MovementTurn(x_coord, y_coord, actions)
        else:
            return ShootingTurn(x_coord, y_coord)

    def turns(self):
        """
        The file might be very large, in which case we want to avoid reading it all
        into memory at the same time. Hence, this function is a generator which reads
        one line at a time and yields one turn object at a time to the process function.
        """
        for line in self.file.readlines():
            yield self.make_turn_from_line(line.strip())

def process_turn(board_size, board, turn_number, turn):
    """
    Runs one turn of the game.
    Mutates the board in place, and returns an action which can 
    be examined for testing.

    Arguments:
        board_size: a positive integer
        board: a dict mapping (x, y): (direction, alive)
        turn_number: an integer (used when throwing exceptions)
        turn: a MovementTurn or ShootingTurn instance

    Returns:
        An action object (e.g. MovedShip) for testing

    Raises:
        InvalidTurn if the turn does not make sense
    """
    if isinstance(turn, MovementTurn):
        return process_move(board_size, board, turn_number, turn)
    elif isinstance(turn, ShootingTurn):
        return process_shoot(board_size, board, turn_number, turn)
    else:
        raise InvalidTurnType()

def process_move(board_size, board, turn_number, turn):
    location = (turn.ship_x, turn.ship_y)
    ship = board.get(location)
    if not ship:
        raise NoShipAtLocation(turn_number, turn.ship_x, turn.ship_y)
    if not ship[1]: # Ship already sunk
        raise MovingSunkShip(turn_number, turn.ship_x, turn.ship_y)
    del board[location]
    direction = ship[0]
    # Back up the initial ship state
    start_direction = direction
    start_location = tuple(location)
    # Now that we have the initial location and direction,
    # loop over the actions and mutate them
    for action in turn.actions:
        if action in ('L', 'R'):
            direction = DIRECTION_TRANSITIONS[direction][action]
        else:
            assert(action == 'M') # Should be guaranteed by the regex
            delta = DIRECTION_DELTAS[direction]
            location = (location[0] + delta[0], location[1] + delta[1])
    # We now have the final location/direction of the ship, so we'll
    # slot it back into the board if the position is valid
    if location[0] < 0 or location[1] < 0 or location[0] >= board_size or location[1] >= board_size:
        raise MoveOutsideBoard(turn_number, location[0], location[1])
    if board.get(location):
        raise ShipAtMoveTarget(turn_number, location[0], location[1])
    # Success
    board[location] = (direction, True)
    return MovedShip(
        start_location[0], start_location[1], start_direction, 
        location[0], location[1], direction
    )

def process_shoot(board_size, board, turn_number, turn):
    ship = board.get((turn.target_x, turn.target_y))
    if not ship:
        return ShotNoTarget(turn.target_x, turn.target_y)
    else:
        was_alive = ship[1]
        # Replace ship with dead ship at location
        board[(turn.target_x, turn.target_y)] = (ship[0], False)
        if was_alive:
            return SunkAliveShip(turn.target_x, turn.target_y)
        else:
            return SunkDeadShip(turn.target_x, turn.target_y)

def run(board_size, initial_ships, turns, actionList=None):
    # Because the board might be very large, it's safer in terms of memory consumption
    # to store a sparse matrix in the form of a dictionary.
    board = {
        (ship.x, ship.y): (ship.direction, ship.alive)
        for ship in initial_ships
    }

    for turn_number, turn in enumerate(turns):
        action = process_turn(board_size, board, turn_number, turn)
        if actionList is not None:
            actionList.append(action)
        
    return board

def main(filename):
    """
    Reads input from the given filename and prints output
    as specified in the problem description.
    """
    with FileReader(filename) as reader:
        final_board = run(reader.board_size, reader.initial_ships, reader.turns())

    # The order in which the ships should be printed is not clear in the question,
    # so I'm just printing them in ascending (x, y) order.
    state = sorted(
        (x, y, direction, alive)
        for (x, y), (direction, alive) in final_board.items()
    )
    for ship_state in state:
        print('(%s, %s, %s)%s' % (
            ship_state[0],
            ship_state[1],
            ship_state[2],
            '' if ship_state[3] else ' SUNK'
        ))

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('Usage: %s <file>' % sys.argv[0])
        sys.exit(1)

    main(sys.argv[1])

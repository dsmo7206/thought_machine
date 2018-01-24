#!/usr/bin/python3

import io
import main
import unittest
import unittest.mock

class ShipGameTests(unittest.TestCase):

    def setUp(self):
        self.basic_ship_x, self.basic_ship_y, self.basic_ship_direction = 5, 5, 'N'
        self.basic_board = {
            (self.basic_ship_x, self.basic_ship_y): (self.basic_ship_direction, True)
        }
        self.basic_board_size = 10

    def tearDown(self):
        del self.basic_board

    # Don't bother testing all transitions - it's just equivalent to redefining
    # main.DIRECTION_TRANSITIONS here and checking equality

    def test_left_rotate(self):
        # Simple left rotation
        action = main.process_turn(
            self.basic_board_size, self.basic_board, 0,
            main.MovementTurn(self.basic_ship_x, self.basic_ship_y, 'L')
        )
        self.assertEqual(
            action,
            main.MovedShip(
                self.basic_ship_x, self.basic_ship_y, self.basic_ship_direction, # Before turn
                self.basic_ship_x, self.basic_ship_y, 'W' # After turn
            )
        )

    def test_ahead_move(self):
        # Simple move 
        action = main.process_turn(
            self.basic_board_size, self.basic_board, 0,
            main.MovementTurn(self.basic_ship_x, self.basic_ship_y, 'M')
        )
        self.assertEqual(
            action,
            main.MovedShip(
                self.basic_ship_x, self.basic_ship_y, self.basic_ship_direction, # Before turn
                self.basic_ship_x, self.basic_ship_y + 1, 'N' # After turn
            )
        )
    
    def test_compound_move(self):
        action = main.process_turn(
            self.basic_board_size, self.basic_board, 0,
            main.MovementTurn(self.basic_ship_x, self.basic_ship_y, 'LLMMMRMMLRM')
        )
        self.assertEqual(
            action,
            main.MovedShip(
                self.basic_ship_x, self.basic_ship_y, self.basic_ship_direction, # Before turn
                self.basic_ship_x - 3, self.basic_ship_y -3, 'W' # After turn
            )
        )

    def test_line_parsing(self):
        # Test with various amounts of whitespace

        self.assertEqual(
            main.FileReader.make_turn_from_line('(123,4)'),
            main.ShootingTurn(123, 4)
        )

        self.assertEqual(
            main.FileReader.make_turn_from_line(' ( 123, 4)  '),
            main.ShootingTurn(123, 4)
        )

        self.assertEqual(
            main.FileReader.make_turn_from_line(' ( 123, 4)LLLRRRMRMMRMRMLRLRLMR'),
            main.MovementTurn(123, 4, 'LLLRRRMRMMRMRMLRLRLMR')
        )

        self.assertEqual(
            main.FileReader.make_turn_from_line(' ( 123, 456  )     LLLRRRMRMMRMRMLRLRLMR'),
            main.MovementTurn(123, 456, 'LLLRRRMRMMRMRMLRLRLMR')
        )

    def test_shoot_empty(self):
        prev_board = dict(self.basic_board)
        action = main.process_turn(
            self.basic_board_size, self.basic_board, 0,
            main.ShootingTurn(self.basic_ship_x + 1, self.basic_ship_y)
        )
        
        self.assertEqual(
            action,
            main.ShotNoTarget(self.basic_ship_x + 1, self.basic_ship_y)
        )
        self.assertEqual(self.basic_board, prev_board)

    def test_shoot_ship(self):
        # Shoot the ship (which is alive)
        prev_board = dict(self.basic_board)

        action = main.process_turn(
            self.basic_board_size, self.basic_board, 0,
            main.ShootingTurn(self.basic_ship_x, self.basic_ship_y)
        )

        self.assertEqual(
            action,
            main.SunkAliveShip(self.basic_ship_x, self.basic_ship_y)
        )
        self.assertEqual(
            self.basic_board,
            {(self.basic_ship_x, self.basic_ship_y): (self.basic_ship_direction, False)}
        )

        # Shoot it again (it's already sunk)
        prev_board = dict(self.basic_board) # Copy
        
        action = main.process_turn(
            self.basic_board_size, self.basic_board, 0,
            main.ShootingTurn(self.basic_ship_x, self.basic_ship_y)
        )

        self.assertEqual(
            action,
            main.SunkDeadShip(self.basic_ship_x, self.basic_ship_y)
        )
        self.assertEqual(self.basic_board, prev_board)

    def test_illegal_moves(self):
        board_size = 8 # Valid coords in range [(0, 0), (7, 7)] 
        board = {
            (2, 2): ('N', True),
            (4, 5): ('E', False) # Sunk already
        }

        # Try moving first ship to (-3, 2)
        with self.assertRaises(main.MoveOutsideBoard) as cm:
            main.process_turn(board_size, dict(board), 0, main.MovementTurn(2, 2, 'LMMMMM'))
        
        self.assertEqual(cm.exception.args, (0, -3, 2))
        
        # Try moving first second (dead) ship
        with self.assertRaises(main.MovingSunkShip) as cm:
            main.process_turn(board_size, dict(board), 0, main.MovementTurn(4, 5, 'LMMMMM'))

        self.assertEqual(cm.exception.args, (0, 4, 5))

        # Try moving ship that doesn't exist
        with self.assertRaises(main.NoShipAtLocation) as cm:
            main.process_turn(board_size, dict(board), 0, main.MovementTurn(1, 2, 'LMMMMM'))

        self.assertEqual(cm.exception.args, (0, 1, 2))

        # Try moving ship into other ship
        with self.assertRaises(main.ShipAtMoveTarget) as cm:
            main.process_turn(board_size, dict(board), 0, main.MovementTurn(2, 2, 'MMMRMM'))

        self.assertEqual(cm.exception.args, (0, 4, 5))


    def test_sample_input(self):
        # Compound test of everything (with very few moves)

        with unittest.mock.patch('sys.stdout', new_callable=io.StringIO) as output:
            main.main('input.txt')

        self.assertEqual(output.getvalue(), '(1, 3, N)\n(9, 2, E) SUNK\n')

if __name__ == '__main__':
    unittest.main()

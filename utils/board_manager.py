import random

from constants import EASY_MODE, INTIMIDATE_MODE, EXPERT_MODE

GENERATE_BOARD_WITHOUT_BOMBS = {EASY_MODE: lambda: generate_board_without_bombs(9, 9),
                                INTIMIDATE_MODE: lambda: generate_board_without_bombs(16, 16),
                                EXPERT_MODE: lambda: generate_board_without_bombs(30, 16)
                                }

MODE_TO_NUMBER_OF_BOMBS = {EASY_MODE: 10,
                           INTIMIDATE_MODE: 40,
                           EXPERT_MODE: 99
                           }


def generate_random_board(mode):
    """A function that gets a mode and generates a random board in this mode."""
    board: list[list] = GENERATE_BOARD_WITHOUT_BOMBS[mode]()
    height = len(board)
    width = len(board[0])
    number_of_bombs = MODE_TO_NUMBER_OF_BOMBS[mode]
    while number_of_bombs > 0:
        row = random.randint(0, height-1)
        column = random.randint(0, width-1)
        if board[row][column] == "SAFE_PLACE":
            board[row][column] = "HIDDEN_BOMB"
            number_of_bombs -= 1
    return board


def generate_board_without_bombs(width, height):
    """A function that generates a board without bombs."""
    board = [[]]
    for row in range(height):
        for column in range(width):
            board[row].append("SAFE_PLACE")
        board.append([])
    board.pop()
    return board

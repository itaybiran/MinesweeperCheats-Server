POINTS_PER_REVEALED_SQUARE = 10
MAX_TIME = 999


def calculate_rank(xp):
    return int((xp // 100)**0.5)


def calculate_game_point(revealed_squares_board, time):
    revealed_squares = 0
    for row in range(len(revealed_squares_board)):
        for column in range(len(revealed_squares_board[0])):
            if revealed_squares_board[row][column] == 1:
                revealed_squares += 1
    return POINTS_PER_REVEALED_SQUARE * revealed_squares + (MAX_TIME - time)

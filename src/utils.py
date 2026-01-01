import random
import pickle
import os

import knucklebones_rust as kb

from src.negamax import get_best_move


def run_random_game(columns_number: int, rows_number: int, max_dice_value: int) -> int:
    game = kb.Knucklebones(columns_number, rows_number, max_dice_value)
    turn_counter = 0
    while not game.is_game_over():
        board_index = random.randint(0, columns_number - 1)
        print(f"Possible moves: {game.get_possible_moves()}")
        print(
            f"Current player: {game.get_current_player()}, dice number: {game.get_dice_value()}, board index: {board_index}"
        )
        game.make_move(board_index)
        turn_counter += 1

        for player_index in range(2):
            print(game.display_board(player_index), end="")
            print(
                f"Number of elements: {game.get_number_of_elements(player_index)}, Score: {game.get_score(player_index)}\n"
            )

    print(f"Game over after {turn_counter} turns")


def run_negamax_game(
    columns_number: int, rows_number: int, max_dice_value: int, depth: int
) -> int:
    game = kb.Knucklebones(columns_number, rows_number, max_dice_value)
    turn_counter = 0

    tt = load_tt("tt.pkl")
    while not game.is_game_over():
        best_move, score = get_best_move(game=game, depth=depth, tt=tt)
        print(
            f"Current player: {game.get_current_player()}, dice number: {game.get_dice_value()}, best move: {best_move}, score: {score:.2f}"
        )
        game.make_move(best_move)
        turn_counter += 1

        for player_index in range(2):
            print(game.display_board(player_index), end="")
            print(
                f"Number of elements: {game.get_number_of_elements(player_index)}, Score: {game.get_score(player_index)}\n"
            )

    print(f"Game over after {turn_counter} turns")

    save_tt(tt, "tt.pkl")


def play_against_negamax(
    columns_number: int, rows_number: int, max_dice_value: int, depth: int
) -> int:
    """Human plays against the negamax agent. The human plays first or second randomly."""
    game = kb.Knucklebones(columns_number, rows_number, max_dice_value)
    player_index = random.randint(0, 1)
    turn_counter = 0

    tt = load_tt("tt.pkl")
    while not game.is_game_over():
        print(f"dice number: {game.get_dice_value()}")
        print(game.display_board(0))
        print("-----")
        print(game.display_board(1))
        if player_index == 0:
            move = int(input("Enter your move: "))
            if not game.make_move(move):
                print("Invalid move")
                continue
        else:
            best_move, _ = get_best_move(game=game, depth=depth, tt=tt)
            game.make_move(best_move)
        player_index = 1 - player_index
        turn_counter += 1

    print(f"Game over after {turn_counter} turns")
    for pi in range(2):
        print(game.display_board(pi), end="")
        print(
            f"Number of elements: {game.get_number_of_elements(pi)}, Score: {game.get_score(pi)}\n"
        )

    print(f"Player {player_index} wins")

    save_tt(tt, "tt.pkl")


def save_tt(tt: dict, filename: str) -> None:
    with open(filename, "wb") as f:
        pickle.dump(tt, f)


def load_tt(filename: str) -> dict:
    if not os.path.exists(filename):
        return {}
    with open(filename, "rb") as f:
        return pickle.load(f)

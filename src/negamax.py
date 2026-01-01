import numpy as np


def other_player(player: int) -> int:
    return 1 if player == 0 else 0


def get_best_move(game: object, depth: int, tt: dict) -> int:
    moves = []
    for column in game.get_available_columns(game.get_current_player()):
        copy_game = game.copy()
        copy_game.make_move(column)
        value = negamax(
            game=copy_game,
            alpha=float("-inf"),
            beta=float("inf"),
            depth=depth,
            current_player=copy_game.get_current_player(),
            tt=tt,
        )
        moves.append((column, value))

    best_move = min(moves, key=lambda x: x[1])
    return best_move[0], -float(best_move[1])


def negamax(
    game: object, alpha: float, beta: float, depth: int, current_player: int, tt: dict
):
    alpha_original = alpha

    tt_entry = tt.get(game.encode_game())
    if tt_entry and tt_entry["depth"] >= depth:
        if tt_entry["flag"] == "EXACT":
            return tt_entry["value"]
        elif tt_entry["flag"] == "LOWERBOUND" and tt_entry["value"] >= beta:
            return tt_entry["value"]
        elif tt_entry["flag"] == "UPPERBOUND" and tt_entry["value"] <= alpha:
            return tt_entry["value"]

    if depth == 0 or game.is_game_over():
        return game.get_heuristic_score(current_player)

    value = float("-inf")
    moves = game.get_possible_moves()
    for dice_value, columns in moves:
        negamax_values = []
        for column in columns:
            copy_game = game.copy()
            copy_game.set_dice_value(dice_value)
            copy_game.make_move(column)

            negamax_values.append(
                -negamax(
                    copy_game,
                    -beta,
                    -alpha,
                    depth - 1,
                    other_player(current_player),
                    tt,
                )
            )

        value = max(value, np.mean(negamax_values))

        alpha = max(alpha, value)
        if alpha >= beta:
            break

    if tt_entry is None:
        tt_entry = {}

    tt_entry["value"] = value
    if value <= alpha_original:
        tt_entry["flag"] = "UPPERBOUND"
    elif value >= beta:
        tt_entry["flag"] = "LOWERBOUND"
    else:
        tt_entry["flag"] = "EXACT"
    tt_entry["depth"] = depth
    tt[game.encode_game()] = tt_entry

    return value

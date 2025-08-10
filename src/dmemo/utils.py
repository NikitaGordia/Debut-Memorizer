import chess
import chess.pgn
import io
import random
from typing import Tuple


def pgn2game(pgn: str) -> chess.pgn.Game:
    return chess.pgn.read_game(io.StringIO(pgn))


def pgn2board(pgn: str) -> chess.Board:
    if len(pgn) == 0:
        return chess.Board()
    return pgn2game(pgn).end().board()


def game2pgn(game: chess.pgn.Game) -> str:
    exporter = chess.pgn.StringExporter(headers=False, variations=False, comments=False)
    pgn_string = game.accept(exporter)
    return pgn_string.rsplit(" ", 1)[0].strip()


def game2uci(game: chess.pgn.Game) -> str:
    if game is None:
        return ""
    uci_moves = [move.uci() for move in game.mainline_moves()]
    return " ".join(uci_moves)


def pgn2uci(pgn: str) -> str:
    game = chess.pgn.read_game(io.StringIO(pgn))
    return game2uci(game)


def uci2board(uci_moves: str) -> chess.Board:
    board = chess.Board()
    if uci_moves:
        for move in uci_moves.split(" "):
            board.push_uci(move)
    return board


def sample_move(distribution: dict[str, int], threshold: float = 0.05) -> str | None:
    if not distribution:
        return None

    dst_sum = sum(distribution.values())
    filtered_dst = {k: v for k, v in distribution.items() if v / dst_sum >= threshold}
    move = random.choices(
        list(filtered_dst.keys()), weights=list(filtered_dst.values()), k=1
    )[0]
    return move, distribution[move]


def previous_move_and_uci(uci_moves: str) -> Tuple[str, str]:
    if not uci_moves or not uci_moves:
        return None, ""

    moves_list = uci_moves.split()

    return moves_list[-1], " ".join(moves_list[:-1])

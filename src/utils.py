import chess
import chess.pgn
import io


def pgn2board(pgn: str) -> chess.Board:
    if len(pgn) == 0:
        return chess.Board()
    game = chess.pgn.read_game(io.StringIO(pgn))
    return game.end().board()

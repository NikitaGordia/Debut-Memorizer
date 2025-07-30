import chess
import chess.pgn
import io


def pgn2board(pgn: str) -> chess.Board:
    if len(pgn) == 0:
        return chess.Board()
    game = chess.pgn.read_game(io.StringIO(pgn))
    return game.end().board()


def get_pgn_moves(game: chess.pgn.Game) -> str:
    """
    Exports the PGN movetext from a chess.pgn.Game object without metadata.

    Args:
        game: A chess.pgn.Game object.

    Returns:
        A string containing the PGN movetext, e.g., "1. e4 e5 2. Nf3 Nc6".
    """
    # The StringExporter is the canonical way to create PGN strings.
    # We disable headers, variations, and comments to get only the main move sequence.
    exporter = chess.pgn.StringExporter(headers=False, variations=False, comments=False)
    pgn_string = game.accept(exporter)
    # The result often includes the game termination marker (e.g., "1-0"), which we can remove.
    return pgn_string.rsplit(" ", 1)[0].strip()


def get_uci_representation(game: chess.pgn.Game) -> str:
    """
    Extracts a space-separated string of moves in UCI notation.

    Args:
        game: A chess.pgn.Game object.

    Returns:
        A space-separated string of UCI moves, e.g., "e2e4 e7e5 g1f3 b8c6".
    """
    # We iterate through the main line of the game and get the UCI string for each move.
    uci_moves = [move.uci() for move in game.mainline_moves()]
    return " ".join(uci_moves)

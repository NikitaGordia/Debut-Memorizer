from flask import Flask
from flask import render_template
from flask import request
import os
from engine import ChessAnalysisPool
from utils import pgn2board, pgn2uci, sample_move
from dotenv import load_dotenv
import chess
from explorer import Explorer
from judge import Judge

load_dotenv()


def create_app():
    app = Flask(__name__)

    app.pool = ChessAnalysisPool(
        book_path=os.environ.get("BOOK_PATH"),
        num_workers=2,
    )
    app.explorer = Explorer(os.environ.get("EXPLORER_CACHE_PATH"), num_workers=2)
    app.judge = Judge(app.pool)
    app.MIN_OCCURRENCES = 10
    app.SAMPLE_THRESHOLD = 0.05
    app.HINT_MULTI_PV = 3

    return app


app = create_app()


def make_move_response(
    sample_move: str, best_prev_moves: list[str], prev_move_diff: float
) -> dict:
    return {
        "sample_move": sample_move,
        "best_prev_moves": " ".join(best_prev_moves),
        "prev_move_diff": prev_move_diff,
    }


def finish_game() -> dict:
    return make_move_response("", [], None)


def continue_game(uci: str, engine_type: str, move_limit: int) -> dict:
    diff = app.judge.last_move_diff(uci, engine_type, move_limit)
    best_moves = app.pool.submit_and_get(
        uci, engine_type, move_limit, app.HINT_MULTI_PV
    )

    moves_dst = app.explorer.submit_and_get(uci)
    if len(moves_dst) == 0:
        print("No moves found, finishing game.")
        return finish_game()

    move, occurrences = sample_move(moves_dst, threshold=app.SAMPLE_THRESHOLD)
    print(f"🧭 Explorer move: {move}, occurrences: {occurrences}")
    if occurrences < app.MIN_OCCURRENCES:
        print("Not enough occurrences, finishing game.")
        return finish_game()

    # Hint
    app.pool.submit_job(f"{uci} {move}", engine_type, move_limit, app.HINT_MULTI_PV)
    # Score to compare
    app.pool.submit_job(f"{uci} {move}", engine_type, move_limit, 1)

    return make_move_response(move, [str(move["pv"][0]) for move in best_moves], diff)


# root(index) route
@app.route("/")
def root():
    return render_template("bbc.html")


# make move API
@app.route("/make_move", methods=["POST"])
def make_move():
    # extract FEN string from HTTP POST request body
    pgn = request.form.get("pgn")
    board = pgn2board(pgn)
    uci = pgn2uci(pgn)

    # extract move time value
    move_time = request.form.get("move_time")
    engine_type = request.form.get("engine_type", "stockfish")

    # if move time is available
    move_limit = 0.1 if move_time == "instant" else int(move_time)

    orientation = (
        chess.WHITE if request.form.get("orientation") == "white" else chess.BLACK
    )
    players_turn = orientation == board.turn

    if players_turn:
        return finish_game()
    else:
        return continue_game(uci, engine_type, move_limit)


# main driver
if __name__ == "__main__":
    # start HTTP server
    app.run(host="0.0.0.0", debug=True, threaded=True)

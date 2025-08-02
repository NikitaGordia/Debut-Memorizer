from flask import Flask
from flask import render_template
from flask import request
from flask import jsonify
import os
from engine import ChessAnalysisPool
from utils import pgn2board, pgn2uci, sample_move, uci2board
from dotenv import load_dotenv
import chess
import random
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

    return app


app = create_app()


def finish_game() -> dict:
    return {}


def surrender(uci: str, engine_type: str, move_limit: int) -> dict:
    moves = app.pool.submit_and_get(uci, engine_type, move_limit)
    if len(moves) == 0:
        raise Exception(
            "Engine returned no moves, uci: {uci}, time_limit: {move_limit}"
        )

    move = random.choice(list(moves))
    print(f"🤖 Engine move: {move}")

    board = uci2board(uci)
    board.push(chess.Move.from_uci(move))
    return {
        "fen": board.fen(),
        "best_move": str(move),
        "continue": False,
    }


def continue_game(uci: str, engine_type: str, move_limit: int) -> dict:
    moves_dst = app.explorer.submit_and_get(uci)
    if len(moves_dst) == 0:
        print("No moves found, finishing game.")
        return finish_game()

    move, occurrences = sample_move(moves_dst)
    print(f"🧭 Explorer move: {move}, occurrences: {occurrences}")
    if occurrences < app.MIN_OCCURRENCES:
        print("Not enough occurrences, finishing game.")
        return finish_game()

    correct_move = app.judge.last_move_is_correct(uci, engine_type, move_limit)

    app.pool.submit_job(f"{uci} {move}", engine_type, move_limit)

    board = uci2board(uci)
    board.push(chess.Move.from_uci(move))

    return {
        "fen": board.fen(),
        "best_move": str(move),
        "continue": correct_move,
    }


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
        return surrender(uci, engine_type, move_limit)
    else:
        return continue_game(uci, engine_type, move_limit)


# main driver
if __name__ == "__main__":
    # start HTTP server
    app.run(debug=True, threaded=True)

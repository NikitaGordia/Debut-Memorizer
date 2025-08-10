from flask import Flask
from flask import render_template
from flask import request
import os
from dmemo.engine import ChessAnalysisPool
from dmemo.utils import pgn2board, pgn2uci, sample_move
from dotenv import load_dotenv
import chess
from dmemo.db.session import init_db
from dmemo.explorer import Explorer
from dmemo.eval import Evaluator

load_dotenv()


def create_app():
    app = Flask(__name__)

    app.pool = ChessAnalysisPool(
        num_workers=6,
    )
    app.explorer = Explorer(os.environ.get("EXPLORER_CACHE_PATH"), num_workers=4)
    app.MIN_OCCURRENCES = 10
    app.SAMPLE_THRESHOLD = 0.05
    app.N_HINTS = 3

    init_db()

    def make_move_response(
        sample_move: str,
        best_prev_moves: list[tuple[str, float]],
        prev_move_diff: float,
    ) -> dict:
        return {
            "sample_move": sample_move,
            "best_prev_moves": best_prev_moves,
            "prev_move_diff": prev_move_diff,
        }

    def finish_game() -> dict:
        return make_move_response(None, [], None)

    def continue_game(
        uci: str, engine_type: str, move_limit: int, training_move: int
    ) -> dict:
        fast_move = training_move <= 1
        evaluator = Evaluator(
            app.pool,
            uci,
            engine_type,
            move_limit,
            n_hints=app.N_HINTS,
            instant=not fast_move,
        )

        moves_dst = app.explorer.submit_and_get(uci)

        diff, best_moves = evaluator.result() if not fast_move else (None, [])

        if len(moves_dst) == 0:
            print("No moves found, finishing game.")
            return make_move_response(None, best_moves, diff)

        move, occurrences = sample_move(moves_dst, threshold=app.SAMPLE_THRESHOLD)
        print(f"🧭 Explorer move: {move}, occurrences: {occurrences}")
        if occurrences < app.MIN_OCCURRENCES:
            print("Not enough occurrences, finishing game.")
            return make_move_response(None, best_moves, diff)

        evaluator.submit_jobs_in_advance(f"{uci} {move}")

        return make_move_response(move, best_moves, diff)

    # root(index) route
    @app.route("/")
    def root():
        return render_template("index.html")

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
        training_move = request.form.get("training_move", type=int)

        # if move time is available
        move_limit = 0.1 if move_time == "instant" else int(move_time)

        orientation = (
            chess.WHITE if request.form.get("orientation") == "white" else chess.BLACK
        )
        players_turn = orientation == board.turn

        if players_turn:
            print("It's player's turn, finishing game...")
            return finish_game()
        else:
            return continue_game(uci, engine_type, move_limit, training_move)

    return app

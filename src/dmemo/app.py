from flask import Flask
from flask import render_template
import os
from dmemo.engine import ChessAnalysisPool
from dmemo.utils import pgn2board, pgn2uci, sample_move
from dotenv import load_dotenv
import chess
from flask_pydantic import validate
from dmemo.db.session import init_db
from dmemo.explorer import Explorer
from dmemo.eval import Evaluator
from dmemo.protocol import MoveRequest

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

    @app.route("/")
    def root():
        return render_template("index.html")

    @app.route("/make_move", methods=["POST"])
    @validate()
    def make_move(body: MoveRequest):
        board = pgn2board(body.pgn)
        uci = pgn2uci(body.pgn)

        orientation = chess.WHITE if body.orientation == "white" else chess.BLACK
        players_turn = orientation == board.turn

        if players_turn:
            print("It's player's turn, finishing game...")
            return finish_game()
        else:
            return continue_game(
                uci, body.engine_type, body.move_time, body.training_move
            )

    return app

from flask import Flask
from flask import render_template
from flask import request
from flask import jsonify
from flask import Response
import json
import os
from engine import ChessAnalysisPool, EngineConfig
from utils import pgn2board, pgn2uci, sample_move
from dotenv import load_dotenv
import chess
from explorer import Explorer
from judge import Judge

load_dotenv()

# create web app instance
app = Flask(__name__)

pool = ChessAnalysisPool(
    engine_config=EngineConfig(
        os.environ.get("ENGINE_PATH"), os.environ.get("ENGINE_WEIGHTS")
    ),
    book_path=os.environ.get("BOOK_PATH"),
    num_workers=2,
)
explorer = Explorer(os.environ.get("EXPLORER_CACHE_PATH"), num_workers=2)
judge = Judge(pool)


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

    # if move time is available
    move_limit = 0.1 if move_time == "instant" else int(move_time)

    orientation = (
        chess.WHITE if request.form.get("orientation") == "white" else chess.BLACK
    )
    players_turn = orientation == board.turn

    if players_turn:
        moves = pool.submit_and_get(uci, move_limit)
        if len(moves) == 0:
            raise Exception("No move found")

        move = moves[0]
        print(f"🤖 Engine move: {move}")
        board.push(move)
        return {
            "fen": board.fen(),
            "best_move": str(move),
            "score": "unknown",
            "depth": 0,
            "pv": "",
            "nodes": "",
            "time": move_limit,
            "judge": {
                "evaluated": False,
                "correct": False,
            },
        }
    else:
        moves_dst = explorer.submit_and_get(uci)
        if len(moves_dst) == 0:
            raise Exception("Implement handling end of opening")
        move = sample_move(moves_dst)
        print(f"🧭 Explorer move: {move}")

        correct = None
        if board.fullmove_number > 2:
            correct = judge.last_move_is_correct(uci, move_limit)
            print(f"⚖️ Correct move: {correct}")

        pool.submit_job(f"{uci} {move}", move_limit)

        board.push(chess.Move.from_uci(move))

        return {
            "fen": board.fen(),
            "best_move": str(move),
            "score": "unknown",
            "depth": 0,
            "pv": "",
            "nodes": "",
            "time": move_limit,
            "judge": {
                "evaluated": correct is not None,
                "correct": correct,
            },
        }


@app.route("/analytics")
def analytics():
    return render_template("stats.html")


@app.route("/analytics/api/post", methods=["POST"])
def post():
    response = Response("")
    response.headers["Access-Control-Allow-Origin"] = "*"

    stats = {
        "Date": request.form.get("date"),
        "Url": request.form.get("url"),
        "Agent": request.headers.get("User-Agent"),
    }

    if request.headers.getlist("X-Forwarded-For"):
        stats["Ip"] = request.headers.getlist("X-Forwarded-For")[0]
    else:
        stats["Ip"] = request.remote_addr

    if request.headers.get("Origin"):
        stats["Origin"] = request.headers.get("Origin")
    else:
        stats["Origin"] = "N/A"

    if request.headers.get("Referer"):
        stats["Referer"] = request.headers.get("Referer")
    else:
        stats["Referer"] = "N/A"

    with open(os.environ.get("STATS_FILE"), "a") as f:
        f.write(json.dumps(stats, indent=2) + "\n\n")
    return response


@app.route("/analytics/api/get")
def get():
    stats = []

    with open(os.environ.get("STATS_FILE")) as f:
        for entry in f.read().split("\n\n"):
            try:
                stats.append(json.loads(entry))
            except:
                pass

    return jsonify({"data": stats})


# main driver
if __name__ == "__main__":
    # start HTTP server
    app.run(debug=True, threaded=True)

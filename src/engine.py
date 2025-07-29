import chess
import chess.engine
import uuid
from concurrent.futures import ThreadPoolExecutor, Future
from typing import Dict, Optional, List
from utils import pgn2board


class Book:
    def __init__(self, book_path: str):
        self.book_path = book_path
        self.book = self._read_book(book_path)

    def _read_book(self, path):
        board = chess.Board()
        with open(path) as f:
            book_raw = f.read()
            games = [
                [chess.Move.from_uci(move) for move in game.split()]
                for game in book_raw.split("\n")[0:-1]
            ]
            pgn_games = [board.variation_san(game) for game in games]

        return pgn_games

    def find(self, pgn):
        moves = []
        board = pgn2board(pgn)
        for game in self.book:
            if game.startswith(pgn) and len(game) > len(pgn):
                if len(pgn) == 0:
                    move = game.split()[1]
                else:
                    white_to_move = game[len(pgn) + 1].isdigit()
                    move = game[len(pgn) :].split()[1 if white_to_move else 0]
                print(f"📖 HERE: {move}", game)
                moves.append(board.parse_san(move))
        return moves


class EngineConfig:
    def __init__(self, executable: str, weights: str):
        self.executable = executable
        self.weights = weights


class ChessAnalysisPool:
    def __init__(
        self, engine_config: EngineConfig, book_path: str, num_workers: int = 2
    ):
        if num_workers <= 0:
            raise ValueError("Number of workers must be a positive integer.")

        self.book = Book(book_path)
        self.engine_config: EngineConfig = engine_config
        self.executor = ThreadPoolExecutor(
            max_workers=num_workers, thread_name_prefix="ChessWorker"
        )

        self._futures: Dict[str, Future] = {}
        print(f"♟️ Chess Analysis Pool initialized with {num_workers} workers.")

    def _setup_engine(self):
        engine = chess.engine.SimpleEngine.popen_uci(self.engine_config.executable)
        engine.configure({"WeightsFile": self.engine_config.weights})
        return engine

    def _run_analysis(self, pgn: str, time_limit: float) -> List[chess.Move]:
        book_moves = self.book.find(pgn)
        if book_moves:
            print(f"📖 Book moves: {book_moves}")
            return book_moves

        engine = self._setup_engine()
        try:
            result = engine.play(pgn2board(pgn), chess.engine.Limit(time=time_limit))
            move = result.move
            print("🤖 Engine move: {move}")
            return [move]
        finally:
            engine.quit()

    def submit_job(self, pgn: str, time_limit: int) -> str:
        future = self.executor.submit(self._run_analysis, pgn, time_limit)

        job_id = str(uuid.uuid4())
        self._futures[job_id] = future

        print(f"Job ...{job_id[:8]} submitted for analysis.")
        return job_id

    def get_result(self, job_id: str) -> List[chess.Move]:
        future = self._futures.pop(job_id, None)
        if not future:
            raise KeyError(f"Job ID '{job_id}' not found or already retrieved.")

        print(f"Waiting for result of job {job_id[:8]}...")
        result = future.result()
        print(f"✅ Result for job {job_id[:8]}... received: {result[0]}")
        return result

    def submit_and_get(self, pgn: str, time_limit: int) -> List[chess.Move]:
        job_id = self.submit_job(pgn, time_limit)
        return self.get_result(job_id)

    def shutdown(self):
        print("Shutting down the thread pool. Waiting for active jobs to finish...")
        self.executor.shutdown(wait=True)
        print("All workers have been shut down.")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown()

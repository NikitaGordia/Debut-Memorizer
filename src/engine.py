import chess
import chess.engine
from concurrent.futures import ThreadPoolExecutor, Future
from typing import Dict, List
from utils import uci2board
from abc import ABC
from dotenv import load_dotenv
import os

load_dotenv()


class Book:
    def __init__(self, book_path: str):
        self.book_path = book_path
        self.book = self._read_book(book_path)

    def _read_book(self, path):
        with open(path) as f:
            book_raw = f.read()
            uci_games = book_raw.split("\n")[0:-1]

        return uci_games

    def find(self, uci: str) -> set[str]:
        moves = []
        for game in self.book:
            if game.startswith(uci) and len(game) > len(uci):
                move = game[len(uci) :].split()[0]
                moves.append(move)
        return set(moves)


class Engine(ABC):
    def __init__(self, path: str):
        self._engine = chess.engine.SimpleEngine.popen_uci(path)

    def analyze(self, uci: str, time_limit: float) -> str:
        result = self._engine.play(uci2board(uci), chess.engine.Limit(time=time_limit))
        move = result.move
        return str(move)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._engine.quit()


class LcZeroEngine(Engine):
    def __init__(self):
        super().__init__(os.environ.get("LCZERO_PATH"))
        self._engine.configure({"WeightsFile": os.environ.get("LCZERO_WEIGHTS")})


class StockfishEngine(Engine):
    def __init__(self):
        super().__init__(os.environ.get("STOCKFISH_PATH"))


def make_engine(engine_type: str) -> Engine:
    if engine_type == "lczero":
        return LcZeroEngine()
    elif engine_type == "stockfish":
        return StockfishEngine()
    else:
        raise ValueError(f"Unknown engine type: {engine_type}")


class ChessAnalysisPool:
    def __init__(self, book_path: str, num_workers: int = 2):
        if num_workers <= 0:
            raise ValueError("Number of workers must be a positive integer.")

        self.book = Book(book_path)
        self.executor = ThreadPoolExecutor(
            max_workers=num_workers, thread_name_prefix="ChessWorker"
        )

        self._futures: Dict[str, Future] = {}
        print(f"♟️ Chess Analysis Pool initialized with {num_workers} workers.")

    def _run_analysis(
        self, uci: str, engine_type: str, time_limit: float
    ) -> List[chess.Move]:
        book_moves = self.book.find(uci)
        if book_moves:
            print(f"📖 Book moves: {book_moves}")
            return book_moves

        with make_engine(engine_type) as engine:
            move = engine.analyze(uci, time_limit)
            print(f"🤖 Engine move: {move}")
            return set(
                [
                    str(move),
                ]
            )

    def submit_job(self, uci: str, engine_type: str, time_limit: int) -> str:
        if uci in self._futures:
            print(f"Job for {uci} already submitted. Reusing job.")
            return uci
        print(f"Job {uci} is submitted.")
        future = self.executor.submit(self._run_analysis, uci, engine_type, time_limit)

        self._futures[uci] = future

    def get_result(self, uci: str) -> List[chess.Move]:
        future = self._futures.pop(uci, None)
        if not future:
            raise KeyError(f"Job ID '{uci}' not found or already retrieved.")

        result = future.result()
        return result

    def submit_and_get(
        self, uci: str, engine_type: str, time_limit: int
    ) -> List[chess.Move]:
        self.submit_job(uci, engine_type=engine_type, time_limit=time_limit)
        return self.get_result(uci)

    def shutdown(self):
        print("Shutting down the thread pool. Waiting for active jobs to finish...")
        self.executor.shutdown(wait=True)
        print("All workers have been shut down.")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown()

from abc import ABC
from concurrent.futures import Future
from concurrent.futures import ThreadPoolExecutor
import os
from typing import Dict

import chess
import chess.engine
from dotenv import load_dotenv

from dmemo.utils import uci2board

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

    def analyze(self, uci: str, time_limit: float, multi_pv: int) -> list[dict]:
        result = self._engine.analyse(uci2board(uci), chess.engine.Limit(time=time_limit), multipv=multi_pv)
        return result

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
    def __init__(self, num_workers: int = 2):
        if num_workers <= 0:
            raise ValueError("Number of workers must be a positive integer.")

        self.executor = ThreadPoolExecutor(max_workers=num_workers, thread_name_prefix="ChessWorker")

        self._futures: Dict[str, Future] = {}
        print(f"♟️ Chess Analysis Pool initialized with {num_workers} workers.")

    @staticmethod
    def job_id(uci: str, multi_pv: int):
        return f"{multi_pv}_{uci}"

    def _run_analysis(self, uci: str, engine_type: str, time_limit: float, multi_pv: int) -> list[dict]:
        with make_engine(engine_type) as engine:
            engine_moves = engine.analyze(uci, time_limit, multi_pv)
            return engine_moves

    def submit_job(self, uci: str, engine_type: str, time_limit: int, multi_pv: int) -> str:
        id = self.job_id(uci, multi_pv)
        if id in self._futures:
            print(f"Job for {uci} already submitted. Reusing job.")
            return id
        print(f"Job {uci} is submitted.")
        self._futures[id] = self.executor.submit(self._run_analysis, uci, engine_type, time_limit, multi_pv)

        return id

    def get_result(self, id: str) -> list[dict]:
        future = self._futures.pop(id, None)
        if not future:
            raise KeyError(f"Job ID '{id}' not found or already retrieved.")

        result = future.result()
        return result

    def submit_and_get(self, uci: str, engine_type: str, time_limit: int, multi_pv: int) -> list[dict]:
        id = self.submit_job(uci, engine_type=engine_type, time_limit=time_limit, multi_pv=multi_pv)
        return self.get_result(id)

    def shutdown(self):
        print("Shutting down the thread pool. Waiting for active jobs to finish...")
        self.executor.shutdown(wait=True)
        print("All workers have been shut down.")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown()

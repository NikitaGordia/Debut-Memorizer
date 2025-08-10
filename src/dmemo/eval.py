from typing import Tuple
from dmemo.utils import previous_move_and_uci, uci2board
from dmemo.engine import ChessAnalysisPool


class Evaluator:
    def __init__(
        self,
        pool: ChessAnalysisPool,
        uci: str,
        engine_type: str,
        move_limit: int,
        n_hints: int,
        instant: bool = False,
    ):
        self.pool = pool
        self.uci = uci
        self.engine_type = engine_type
        self.move_limit = move_limit
        self.n_hints = n_hints

        _, self.prev_uci = previous_move_and_uci(uci)
        self.pov = uci2board(self.prev_uci).turn

        self.ids = []

        if instant:
            self.submit_jobs()

    def submit_jobs_in_advance(self, uci: str):
        # Best moves (hints)
        self.pool.submit_job(uci, self.engine_type, self.move_limit, self.n_hints)
        # Base score for the next move
        self.pool.submit_job(
            uci, self.engine_type, time_limit=self.move_limit, multi_pv=1
        )

    def submit_jobs(self):
        best_moves_id = self.pool.submit_job(
            self.prev_uci, self.engine_type, self.move_limit, self.n_hints
        )
        prev_id = self.pool.submit_job(
            self.prev_uci, self.engine_type, time_limit=self.move_limit, multi_pv=1
        )
        curr_id = self.pool.submit_job(
            self.uci, self.engine_type, time_limit=self.move_limit, multi_pv=1
        )
        self.ids = (best_moves_id, prev_id, curr_id)

    def result(self) -> Tuple[float, list[tuple[str, float]]]:
        best_moves_id, prev_id, curr_id = self.ids
        prev_state = self.pool.get_result(prev_id)
        curr_state = self.pool.get_result(curr_id)

        prev_score = prev_state[0]["score"].pov(self.pov).score()
        curr_score = curr_state[0]["score"].pov(self.pov).score()

        best_moves = self.pool.get_result(best_moves_id)

        best_moves = [
            (
                str(move["pv"][0]),
                min(move["score"].pov(self.pov).score() - prev_score, 0),
            )
            for move in best_moves
        ]

        return min(curr_score - prev_score, 0), best_moves

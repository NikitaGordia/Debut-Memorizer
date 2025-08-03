from utils import previous_move_and_uci
from engine import ChessAnalysisPool

DEFAULT_MOVE_LIMIT = 3


class Judge:
    def __init__(self, pool: ChessAnalysisPool):
        self.pool = pool

    def last_move_is_correct(
        self, uci: str, engine_type: str, move_limit: int, multi_pv: int
    ) -> bool:
        last_move, prev_uci = previous_move_and_uci(uci)
        best_moves = self.pool.submit_and_get(
            prev_uci, engine_type, time_limit=move_limit, multi_pv=multi_pv
        )
        print("Judge: last=", last_move, "best=", best_moves)
        return last_move in best_moves, best_moves

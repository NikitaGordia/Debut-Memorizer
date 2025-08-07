from utils import previous_move_and_uci, uci2board
from engine import ChessAnalysisPool


class Judge:
    def __init__(self, pool: ChessAnalysisPool):
        self.pool = pool

    def last_move_diff(self, uci: str, engine_type: str, move_limit: int) -> float:
        _, prev_uci = previous_move_and_uci(uci)
        prev_id = self.pool.submit(
            prev_uci, engine_type, time_limit=move_limit, multi_pv=1
        )
        curr_id = self.pool.submit(uci, engine_type, time_limit=move_limit, multi_pv=1)

        prev_state = self.pool.get_result(prev_id)
        curr_state = self.pool.get_result(curr_id)
        board = uci2board(prev_uci)
        pov = board.turn

        prev_score = prev_state[0]["score"].pov(pov).score()
        curr_score = curr_state[0]["score"].pov(pov).score()

        return abs(curr_score - prev_score)

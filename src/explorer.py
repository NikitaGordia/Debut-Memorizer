import argparse
import db
import diskcache as dc
import tqdm
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
import os

load_dotenv()


class Explorer:
    def __init__(self, cache_path: str, num_workers: int = 2):
        self.executor = ThreadPoolExecutor(
            max_workers=num_workers, thread_name_prefix="ExprorerWorker"
        )
        self.cache = dc.Cache(cache_path)
        self.futures = {}

    def _explore(self, uci):
        if uci in self.cache:
            return self.cache[uci]
        moves = db.get_next_move_distribution(uci)
        self.cache[uci] = moves
        return moves

    def submit_job(self, uci: str) -> None:
        future = self.executor.submit(self._explore, uci)
        self.futures[uci] = future

    def get_result(self, uci: str) -> dict[str, int]:
        future = self.futures.pop(uci, None)
        if not future:
            raise KeyError(f"UCI '{uci}' not found or already retrieved.")
        return future.result()

    def submit_and_get(self, uci: str) -> dict[str, int]:
        self.submit_job(uci)
        return self.get_result(uci)

    def _recursive_explore(
        self,
        uci: str,
        depth: int,
        max_depth: int,
        stop_threshold: float,
        pbar: tqdm.tqdm,
    ):
        dst = self.get_result(uci)
        pbar.update(1)
        total = sum(dst.values())
        if total == 0:
            return

        if depth + 1 > max_depth:
            return

        for move, count in dst.items():
            if count / total < stop_threshold:
                continue
            new_uci = f"{uci} {move}" if uci else move
            self.submit_job(new_uci)
            self._recursive_explore(new_uci, depth + 1, max_depth, stop_threshold, pbar)

    def explore(self, uci: str, depth: int, stop_threshold: float) -> dict[str, int]:
        self.submit_job(uci)

        pbar = tqdm.tqdm(desc="🧭 Exploring", unit="positions")
        self._recursive_explore(uci, 0, depth, stop_threshold, pbar)
        pbar.close()

    def shutdown(self):
        print("Shutting down the thread pool. Waiting for active jobs to finish...")
        self.executor.shutdown(wait=True)
        print("All workers have been shut down.")


def explore(depth: int, num_workers: int, stop_threshold: float) -> dict[str, int]:
    explorer = Explorer(os.environ.get("EXPLORER_CACHE_PATH"), num_workers)
    explorer.explore("", depth, stop_threshold)
    explorer.shutdown()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Multi-threaded explorer of moves distribution.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--num-workers",
        type=int,
        default=os.cpu_count() // 2,
        help="Number of worker processes to use for parsing.",
    )
    parser.add_argument(
        "--depth",
        type=int,
        default=3,
        help="Depth of the exploration.",
    )
    parser.add_argument(
        "--stop-threshold",
        type=float,
        default=0.05,
        help="Minimum ratio of occurances to continue exploration.",
    )
    args = parser.parse_args()

    explore(args.depth, args.num_workers, args.stop_threshold)

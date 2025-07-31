import argparse
import chess.pgn
import tqdm
import io
import os
from multiprocessing import Pool, cpu_count
from typing import Generator, Tuple, List
from functools import partial
from datetime import datetime

from .models import Game
from . import add_games
from src.utils import game2uci, game2pgn

DB_BATCH_SIZE = 1_000_000
CHUNK_SIZE = 10_000_000


def parse_date_from_pgn(date_str):
    if not date_str or date_str == "????.??.??":
        return None
    try:
        return datetime.strptime(date_str, "%Y.%m.%d").date()
    except ValueError:
        return None


def process_game(game: chess.pgn.Game) -> Game:
    headers = game.headers
    return Game(
        uci=game2uci(game),
        pgn=game2pgn(game),
        event=headers.get("Event"),
        site=headers.get("Site"),
        date=parse_date_from_pgn(headers.get("Date")),
        white=headers.get("White"),
        black=headers.get("Black"),
        result=headers.get("Result"),
        utc_date=parse_date_from_pgn(headers.get("UTCDate")),
        utc_time=headers.get("UTCTime"),
        white_elo=headers.get("WhiteElo"),
        black_elo=headers.get("BlackElo"),
        white_rating_diff=headers.get("WhiteRatingDiff"),
        black_rating_diff=headers.get("BlackRatingDiff"),
        eco=headers.get("ECO"),
        opening=headers.get("Opening"),
        time_control=headers.get("TimeControl"),
        termination=headers.get("Termination"),
    )


def find_game_chunks(
    file_path: str, chunk_size: int
) -> Generator[Tuple[int, int], None, None]:
    file_size = os.path.getsize(file_path)
    if file_size == 0:
        return

    start_pos = 0

    with open(file_path, "rb") as f:
        while start_pos < file_size:
            end_pos = min(start_pos + chunk_size, file_size)
            if end_pos < file_size:
                f.seek(end_pos)
                while True:
                    line = f.readline()
                    if not line or (b"[Event " in line):
                        end_pos = f.tell() - len(line)
                        break

            yield (start_pos, end_pos)

            start_pos = end_pos
            if start_pos >= file_size:
                break


def process_chunk(path, positions) -> List[Game]:
    start_pos, end_pos = positions
    processed_games = []
    with open(path, "r", encoding="utf-8-sig") as f:
        f.seek(start_pos)
        chunk_text = f.read(end_pos - start_pos)
        pgn_io = io.StringIO(chunk_text)

        while True:
            try:
                game = chess.pgn.read_game(pgn_io)
                if game is None:
                    break
                processed_games.append(process_game(game))
            except Exception:
                continue

    return processed_games


def import_games_parallel(path: str, num_workers: int, total: int = None):
    print(f"Starting parallel import with {num_workers} workers...")

    chunk_generator = find_game_chunks(path, CHUNK_SIZE)

    games_buffer = []
    games_processed_count = 0
    pbar = tqdm.tqdm(total=total, desc="⚙️ Processing Games", unit="games")

    with Pool(processes=num_workers) as pool:
        for processed_games_list in pool.imap_unordered(
            partial(process_chunk, path), chunk_generator
        ):
            if processed_games_list:
                games_buffer.extend(processed_games_list)
                games_processed_count += len(processed_games_list)
                pbar.update(len(processed_games_list))

                if len(games_buffer) >= DB_BATCH_SIZE:
                    add_games(games_buffer)
                    games_buffer.clear()

    if games_buffer:
        add_games(games_buffer)
        games_buffer.clear()

    pbar.close()
    print(f"\n✅ Finished. Imported a total of {games_processed_count} games.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="High-performance parallel importer for PGN files.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("file", help="PGN file to import")
    parser.add_argument(
        "--num-workers",
        type=int,
        default=cpu_count(),
        help="Number of worker processes to use for parsing.",
    )
    parser.add_argument(
        "--total",
        type=int,
        help="Total number of games for the progress bar.",
        default=None,
    )
    args = parser.parse_args()

    import_games_parallel(args.file, args.num_workers, args.total)

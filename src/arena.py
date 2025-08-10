import chess
import chess.engine
import yaml
import concurrent.futures
from tqdm import tqdm
import os
import math
import itertools
from dataclasses import dataclass
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()

ENGINES = {
    "stockfish": os.environ.get("STOCKFISH_PATH"),
    "lczero": os.environ.get("LCZERO_PATH"),
}


@dataclass
class Player:
    name: str
    engine: str
    options: Dict[str, Any]
    time_limit: float
    elo: float = 400.0
    games_played: int = 0
    score: float = 0.0

    def get_configured_engine(self) -> chess.engine.SimpleEngine:
        if self.engine not in ENGINES:
            raise ValueError(f"Unknown engine: {self.engine}")
        engine = chess.engine.SimpleEngine.popen_uci(ENGINES[self.engine])
        engine.configure(self.options or {})
        return engine


def play_game(white_player: Player, black_player: Player) -> float:
    try:
        with (
            white_player.get_configured_engine() as white_engine,
            black_player.get_configured_engine() as black_engine,
        ):
            board = chess.Board()
            while not board.is_game_over(claim_draw=True):
                if board.turn == chess.WHITE:
                    limit = chess.engine.Limit(time=white_player.time_limit)
                    result = white_engine.play(board, limit)
                else:
                    limit = chess.engine.Limit(time=black_player.time_limit)
                    result = black_engine.play(board, limit)
                board.push(result.move)
            result = board.result(claim_draw=True)
            if result == "1-0":
                return 1.0
            elif result == "0-1":
                return 0.0
            else:
                return 0.5
    except Exception as e:
        print(
            f"An error occurred during a game between {white_player.name} and {black_player.name}: {e}"
        )
        return 0.5


def update_elo(
    player_a_elo: float, player_b_elo: float, score_a: float, k_factor: int
) -> tuple[float, float]:
    expected_a = 1 / (1 + math.pow(10, (player_b_elo - player_a_elo) / 400))
    new_a_elo = player_a_elo + k_factor * (score_a - expected_a)
    new_b_elo = player_b_elo + k_factor * ((1.0 - score_a) - (1 - expected_a))
    return new_a_elo, new_b_elo


def main():
    print("🚀 Starting Multi-Engine Elo Benchmark")

    try:
        with open("../config/arena.yaml", "r") as f:
            config = yaml.safe_load(f)
    except FileNotFoundError:
        print("❌ Error: config.yaml not found. Please create it.")
        return

    opts = config["tournament_options"]
    k_factor = opts["k_factor"]
    initial_elo = opts["initial_elo"]
    total_games_per_pair = opts["total_games"]
    max_workers = opts["concurrency"]

    if total_games_per_pair % 2 != 0:
        print("❌ Error: 'total_games' must be an even number.")
        return
    games_as_each_color = total_games_per_pair // 2

    # 2. Initialize Players (UPDATED LOGIC)
    players = {}
    print("⚙️  Loading and validating player configurations...")
    for p_config in config["players"]:
        player_name = p_config.get("name")

        players[player_name] = Player(
            name=player_name,
            engine=p_config.get("engine"),
            options=p_config.get("options", {}),
            time_limit=p_config["time_limit"],
            elo=initial_elo,
        )

    if len(players) < 2:
        print(
            "❌ Error: Not enough valid players to start a tournament (need at least 2). Check engine_path in config.yaml."
        )
        return

    player_names = list(players.keys())

    # 3. Create All Matchups
    matchups = []
    for p1_name, p2_name in itertools.combinations(player_names, 2):
        for _ in range(games_as_each_color):
            matchups.append((p1_name, p2_name))
        for _ in range(games_as_each_color):
            matchups.append((p2_name, p1_name))

    print(f"📊 Tournament Setup: {len(players)} players, {len(matchups)} total games.")

    # 4. Run Games in Parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_match = {
            executor.submit(play_game, players[white_name], players[black_name]): (
                white_name,
                black_name,
            )
            for white_name, black_name in matchups
        }

        results = []
        print(
            f"⚔️  Running {len(matchups)} games with up to {max_workers} parallel threads..."
        )
        for future in tqdm(
            concurrent.futures.as_completed(future_to_match), total=len(matchups)
        ):
            white_name, black_name = future_to_match[future]
            try:
                white_score = future.result()
                results.append((white_name, black_name, white_score))
            except Exception as e:
                print(
                    f"An error occurred fetching result for {white_name} vs {black_name}: {e}"
                )

    # 5. Calculate Elo ratings
    print("\n✅ All games finished. Calculating Elo ratings...")
    for white_name, black_name, white_score in results:
        p_white = players[white_name]
        p_black = players[black_name]

        p_white.score += white_score
        p_black.score += 1.0 - white_score
        p_white.games_played += 1
        p_black.games_played += 1

        new_elo_white, new_elo_black = update_elo(
            p_white.elo, p_black.elo, white_score, k_factor
        )
        p_white.elo = new_elo_white
        p_black.elo = new_elo_black

    # 6. Display Final Results
    print("\n--- Final Results ---")
    sorted_players = sorted(players.values(), key=lambda p: p.elo, reverse=True)

    print(f"{'Rank':<5} {'Name':<20} {'Elo':<10} {'Score':<15} {'Games':<5}")
    print("-" * 60)
    for i, p in enumerate(sorted_players):
        rank = i + 1
        score_str = f"{p.score:.1f}/{p.games_played}"
        print(
            f"{rank:<5} {p.name:<20} {p.elo:<10.2f} {score_str:<15} {p.games_played:<5}"
        )


if __name__ == "__main__":
    main()

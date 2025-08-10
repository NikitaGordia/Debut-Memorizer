from sqlalchemy import func, desc
from dmemo.db.models import Game
from dmemo.db.session import make_session


def add_game(game: Game):
    with make_session() as session:
        session.add(game)
        session.commit()


def add_games(games: list[Game]):
    with make_session() as session:
        session.add_all(games)
        session.commit()


def get_next_move_distribution(opening_uci: str) -> dict[str, int]:
    with make_session() as session:
        opening_uci = opening_uci.strip()

        num_opening_moves = len(opening_uci.split()) if opening_uci else 0
        next_move_index = num_opening_moves + 1

        next_move_expr = func.split_part(Game.uci, " ", next_move_index).label(
            "next_move"
        )

        query = session.query(next_move_expr, func.count(Game.id).label("move_count"))

        if opening_uci:
            query = query.filter(Game.uci.like(f"{opening_uci} %"))

        query = query.group_by(next_move_expr)

        query = query.filter(next_move_expr != "")

        query = query.order_by(desc("move_count"))

        results = query.all()
        return {move: count for move, count in results}

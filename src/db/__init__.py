import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, func, desc
from sqlalchemy.orm import sessionmaker
from db.models import Game, Base

load_dotenv()

DATABASE_URL = f"postgresql://{os.environ.get('POSTGRES_USER')}:{os.environ.get('POSTGRES_PASSWORD')}@localhost:5432/{os.environ.get('POSTGRES_DB')}"

engine = create_engine(DATABASE_URL)
Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)


def add_game(game: Game):
    with Session() as session:
        session.add(game)
        session.commit()


def add_games(games: list[Game]):
    with Session() as session:
        session.add_all(games)
        session.commit()


def get_next_move_distribution(opening_uci: str) -> dict[str, int]:
    with Session() as session:
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

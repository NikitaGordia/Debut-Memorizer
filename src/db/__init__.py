import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .models import Game, Base

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

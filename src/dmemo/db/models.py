from sqlalchemy import Column
from sqlalchemy import Date
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Time
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Game(Base):
    __tablename__ = "games"

    id = Column(Integer, primary_key=True)
    uci = Column(String)
    pgn = Column(String)

    event = Column(String)
    site = Column(String)
    date = Column(Date)
    white = Column(String)
    black = Column(String)
    result = Column(String)
    utc_date = Column(Date)
    utc_time = Column(Time)
    white_elo = Column(Integer)
    black_elo = Column(Integer)
    white_rating_diff = Column(String)
    black_rating_diff = Column(String)
    eco = Column(String)
    opening = Column(String)
    time_control = Column(String)
    termination = Column(String)

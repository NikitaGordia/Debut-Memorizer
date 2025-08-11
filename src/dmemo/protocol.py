from typing import Literal
from typing import Annotated
from pydantic import BaseModel, Field
import io
import chess.pgn
from pydantic import field_validator


class MoveRequest(BaseModel):
    pgn: Annotated[
        str,
        Field(
            strict=True, description="PGN string representing the current game state"
        ),
    ]
    orientation: Annotated[
        Literal["white", "black"],
        Field(description="Orientation of the board"),
    ]
    move_time: Annotated[
        float,
        Field(
            strict=True,
            ge=0.1,
            le=90,
            description="Move time in seconds (0.1-90)",
        ),
    ]
    engine_type: Annotated[
        Literal["stockfish", "lczero"],
        Field(description="Type of chess engine to use"),
    ]
    training_move: Annotated[
        int,
        Field(
            strict=True, ge=0, description="Current move number in the training session"
        ),
    ]

    @field_validator("pgn")
    def validate_pgn(cls, v):
        try:
            if chess.pgn.read_game(io.StringIO(v)) is None:
                raise ValueError
        except Exception:
            raise ValueError("Invalid PGN string")
        return v

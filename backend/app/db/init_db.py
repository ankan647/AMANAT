from sqlalchemy.engine import Engine

from app.db.base import Base
from app.db.models import AnchorBase
from app.db.triggers import install_anchor_triggers, install_triggers


def init_main_db(engine: Engine) -> None:
    Base.metadata.create_all(engine)
    install_triggers(engine)


def init_anchor_db(engine: Engine) -> None:
    AnchorBase.metadata.create_all(engine)
    install_anchor_triggers(engine)

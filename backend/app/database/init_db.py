from app.database.database import Base, engine

# Import models so SQLAlchemy knows which tables to create.
from app.database import models


def init_db():
    Base.metadata.create_all(bind=engine)
    print("TalkBridge database tables initialized successfully.")
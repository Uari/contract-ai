# tools/create_tables.py
from app.db import engine, Base
from app import models  # noqa

if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    print("✅ tables created")

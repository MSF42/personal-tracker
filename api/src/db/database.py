import aiosqlite

DATABASE_PATH = "data/tracker.db"


async def get_db():
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Configure the connection (WAL mode, foreign keys, row factory)
        await db.execute("PRAGMA journal_mode = WAL")
        await db.execute("PRAGMA foreign_keys = ON")
        db.row_factory = aiosqlite.Row  # Makes rows dict-like
        yield db  # yield, not return - this is a dependency
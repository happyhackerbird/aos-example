import os

import pytest

from notes import db


@pytest.fixture
def conn():
    if not os.environ.get("DATABASE_URL"):
        pytest.fail("DATABASE_URL is not set; run `export DATABASE_URL=$(scripts/db.sh up)` first")
    with db.connect() as connection:
        db.migrate(connection)
        db.reset(connection)
        db.seed(connection)
        yield connection

import os
import psycopg2
from psycopg2.extras import RealDictCursor


def get_connection():
    """Single connection per request. Fine at this scale (one class, low traffic);
    revisit with a connection pool (e.g. psycopg2.pool) if usage grows."""
    return psycopg2.connect(os.environ["DATABASE_URL"], cursor_factory=RealDictCursor)

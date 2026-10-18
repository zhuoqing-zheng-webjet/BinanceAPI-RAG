"""Database connection and schema."""

import psycopg
from pgvector.psycopg import register_vector

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS chunks (
    id            bigserial PRIMARY KEY,
    doc_path      text NOT NULL,   -- e.g. 'rest-api.md'
    heading_path  text NOT NULL,   -- e.g. 'Trading endpoints > New order (TRADE)'
    part          int  NOT NULL,   -- 1, 2, ... when a long section is split
    url           text NOT NULL,   -- GitHub link with #anchor
    content       text NOT NULL,
    token_count   int  NOT NULL,
    embedding     vector({dims}) NOT NULL,
    -- Full-text search column, computed by Postgres on insert and stored.
    -- Heading words get weight A and body words weight B, so ts_rank scores a
    -- match in the heading higher than the same word in the body.
    tsv tsvector GENERATED ALWAYS AS (
        setweight(to_tsvector('english', heading_path), 'A') ||
        setweight(to_tsvector('english', content), 'B')
    ) STORED,
    source_commit text NOT NULL
);

-- Inverted index for keyword search (tsv @@ query).
CREATE INDEX IF NOT EXISTS chunks_tsv_idx ON chunks USING gin (tsv);

-- No vector index on purpose: with ~700 chunks, exact search over every
-- embedding takes milliseconds, and an approximate index (HNSW) could miss
-- results. Revisit if the corpus grows by orders of magnitude.
"""


def connect(database_url: str) -> psycopg.Connection:
    conn = psycopg.connect(database_url)
    conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
    register_vector(conn)  # lets psycopg send/receive vector values as lists/arrays
    return conn


def init_db(conn: psycopg.Connection, dims: int) -> None:
    conn.execute(SCHEMA_SQL.format(dims=int(dims)))
    conn.commit()

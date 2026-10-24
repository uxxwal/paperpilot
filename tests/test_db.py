from paperpilot.db import get_conn


def test_db_has_tables():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema='public';"
        ).fetchall()
        names = {r[0] for r in rows}
        assert {"papers", "chunks"} <= names

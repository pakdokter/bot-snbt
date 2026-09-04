from contextlib import contextmanager

from psycopg2.extras import RealDictCursor
from psycopg2.pool import SimpleConnectionPool

from config import DATABASE_URL

_pool = SimpleConnectionPool(1, 5, dsn=DATABASE_URL)


@contextmanager
def get_conn():
    conn = _pool.getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _pool.putconn(conn)


def q(sql, params=None, fetch=None):
    """fetch: None | 'one' | 'all'"""
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params or ())
            if fetch == "one":
                return cur.fetchone()
            if fetch == "all":
                return cur.fetchall()
            return None


# ---------- USERS ----------

def get_user(telegram_id: int):
    return q("SELECT * FROM users WHERE telegram_id = %s", (telegram_id,), fetch="one")


def create_user(telegram_id: int, nama: str, username: str,
                role: str = "user", status: str = "pending"):
    return q(
        """INSERT INTO users (telegram_id, nama, username, role, status)
           VALUES (%s, %s, %s, %s, %s)
           ON CONFLICT (telegram_id) DO NOTHING
           RETURNING *""",
        (telegram_id, nama, username, role, status),
        fetch="one",
    )


def set_user_status(telegram_id: int, status: str, admin_id: int | None = None):
    return q(
        """UPDATE users
           SET status = %s,
               approved_by = (SELECT id FROM users WHERE telegram_id = %s),
               approved_at = CASE WHEN %s = 'approved' THEN now() ELSE approved_at END
           WHERE telegram_id = %s
           RETURNING *""",
        (status, admin_id, status, telegram_id),
        fetch="one",
    )


def list_users(status: str):
    return q(
        "SELECT * FROM users WHERE status = %s ORDER BY created_at",
        (status,),
        fetch="all",
    )


def list_admin_ids():
    rows = q(
        "SELECT telegram_id FROM users WHERE role = 'admin' AND status = 'approved'",
        fetch="all",
    )
    return [r["telegram_id"] for r in rows]


# ---------- TAKSONOMI ----------

def list_mapel():
    return q("SELECT * FROM mapel ORDER BY urutan", fetch="all")


def list_part(mapel_id: int):
    return q(
        "SELECT * FROM part WHERE mapel_id = %s ORDER BY urutan",
        (mapel_id,),
        fetch="all",
    )


def get_part(part_id: int):
    return q(
        """SELECT p.*, m.kode AS mapel_kode, m.nama AS mapel_nama
           FROM part p JOIN mapel m ON m.id = p.mapel_id
           WHERE p.id = %s""",
        (part_id,),
        fetch="one",
    )

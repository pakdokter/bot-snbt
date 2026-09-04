import json
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


# ---------- STATISTIK ----------

def get_stats():
    def satu(sql):
        return q(sql, fetch="one")["n"]

    return {
        "user_approved":   satu("SELECT count(*) n FROM users WHERE status='approved'"),
        "user_pending":    satu("SELECT count(*) n FROM users WHERE status='pending'"),
        "soal_verified":   satu("SELECT count(*) n FROM soal WHERE status='verified'"),
        "soal_tanpa_kunci":satu("SELECT count(*) n FROM soal WHERE status='verified' AND status_kunci='belum'"),
        "jumlah_variasi":  satu("SELECT count(*) n FROM variasi"),
        "jumlah_paket":    satu("SELECT count(*) n FROM paket"),
        "materi_verified": satu("SELECT count(*) n FROM materi WHERE status='verified'"),
        "soal_per_mapel": q(
            """SELECT m.nama, count(s.id) AS jumlah
               FROM mapel m
               LEFT JOIN part p ON p.mapel_id = m.id
               LEFT JOIN soal s ON s.part_id = p.id AND s.status = 'verified'
               GROUP BY m.id, m.nama, m.urutan
               ORDER BY m.urutan""",
            fetch="all",
        ),
    }


# ---------- INTAKE ----------

def create_intake(uploaded_by_tid: int, jenis: str, file_type: str, file_id_tg: str):
    return q(
        """INSERT INTO intake (uploaded_by, jenis, file_type, file_id_tg, status)
           VALUES ((SELECT id FROM users WHERE telegram_id = %s), %s, %s, %s, 'extracting')
           RETURNING *""",
        (uploaded_by_tid, jenis, file_type, file_id_tg),
        fetch="one",
    )


def update_intake_raw(intake_id: int, raw_text: str):
    q("UPDATE intake SET raw_text = %s WHERE id = %s", (raw_text, intake_id))


def update_intake_klasifikasi(intake_id: int, klasifikasi: dict, tipe_sumber: str, status: str):
    q(
        "UPDATE intake SET klasifikasi_ai = %s, tipe_sumber = %s, status = %s WHERE id = %s",
        (json.dumps(klasifikasi), tipe_sumber, status, intake_id),
    )


def update_intake_status(intake_id: int, status: str):
    q("UPDATE intake SET status = %s WHERE id = %s", (status, intake_id))


def get_intake(intake_id: int):
    return q("SELECT * FROM intake WHERE id = %s", (intake_id,), fetch="one")


def list_intake_menunggu():
    return q(
        "SELECT * FROM intake WHERE status = 'menunggu_admin' ORDER BY created_at",
        fetch="all",
    )


def count_soal_by_intake(intake_id: int):
    return q(
        """SELECT m.nama AS mapel_nama, p.nama AS part_nama, count(s.id) AS jumlah
           FROM soal s
           JOIN part p ON p.id = s.part_id
           JOIN mapel m ON m.id = p.mapel_id
           WHERE s.intake_id = %s
           GROUP BY m.id, m.nama, p.id, p.nama, m.urutan, p.urutan
           ORDER BY m.urutan, p.urutan""",
        (intake_id,),
        fetch="all",
    )


# ---------- TAKSONOMI: lookup by kode ----------

def find_mapel_by_kode(kode: str):
    return q("SELECT * FROM mapel WHERE kode = %s", (kode,), fetch="one")


def find_part_by_kode(mapel_id: int, part_kode: str):
    return q(
        "SELECT * FROM part WHERE mapel_id = %s AND kode = %s",
        (mapel_id, part_kode),
        fetch="one",
    )


# ---------- SOAL ----------

def next_seq_soal(part_id: int) -> int:
    return q("SELECT count(*) n FROM soal WHERE part_id = %s", (part_id,), fetch="one")["n"] + 1


def insert_soal(kode, part_id, intake_id, teks_soal, opsi, kunci, status, verified_by_tid=None):
    return q(
        """INSERT INTO soal (kode, part_id, intake_id, teks_soal, opsi, kunci,
                             status, status_kunci, verified_by)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s,
                   (SELECT id FROM users WHERE telegram_id = %s))
           RETURNING *""",
        (kode, part_id, intake_id, teks_soal, json.dumps(opsi) if opsi else None,
         kunci, status, "draft_ai" if kunci else "belum", verified_by_tid),
        fetch="one",
    )


def set_soal_google_doc(soal_id, doc_id):
    q("UPDATE soal SET google_doc_id = %s WHERE id = %s", (doc_id, soal_id))


# ---------- MATERI ----------

def next_seq_materi(part_id: int) -> int:
    return q("SELECT count(*) n FROM materi WHERE part_id = %s", (part_id,), fetch="one")["n"] + 1


def insert_materi(kode, part_id, intake_id, judul, konten, status, verified_by_tid=None):
    return q(
        """INSERT INTO materi (kode, part_id, intake_id, judul, konten, status, verified_by)
           VALUES (%s, %s, %s, %s, %s, %s, (SELECT id FROM users WHERE telegram_id = %s))
           RETURNING *""",
        (kode, part_id, intake_id, judul, konten, status, verified_by_tid),
        fetch="one",
    )


def set_materi_google_doc(materi_id, doc_id):
    q("UPDATE materi SET google_doc_id = %s WHERE id = %s", (doc_id, materi_id))

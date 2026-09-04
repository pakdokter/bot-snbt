-- ============================================
-- 001_init.sql — Bot Bank Soal UTBK/SNBT
-- PostgreSQL (Railway)
-- ============================================

-- USERS & AUTH
CREATE TABLE users (
    id              SERIAL PRIMARY KEY,
    telegram_id     BIGINT UNIQUE NOT NULL,
    nama            TEXT,
    username        TEXT,
    role            TEXT NOT NULL DEFAULT 'user',      -- 'admin' | 'user'
    status          TEXT NOT NULL DEFAULT 'pending',   -- 'pending' | 'approved' | 'blocked'
    approved_by     INTEGER REFERENCES users(id),
    approved_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- TAKSONOMI (mengikuti struktur daftar isi buku)
CREATE TABLE mapel (
    id              SERIAL PRIMARY KEY,
    kode            TEXT UNIQUE NOT NULL,   -- 'PU', 'PK', 'PM', 'PPU', 'PBM', 'LBI', 'LBE'
    nama            TEXT NOT NULL,          -- 'Penalaran Umum', dst.
    urutan          INTEGER NOT NULL
);

CREATE TABLE part (
    id              SERIAL PRIMARY KEY,
    mapel_id        INTEGER NOT NULL REFERENCES mapel(id),
    kode            TEXT NOT NULL,          -- 'B1', 'B2', ... 'SIM'
    nama            TEXT NOT NULL,          -- 'Penalaran Deduktif', dst.
    urutan          INTEGER NOT NULL,
    UNIQUE (mapel_id, kode)
);

-- ANTRIAN INTAKE (file masuk sebelum diverifikasi admin)
CREATE TABLE intake (
    id              SERIAL PRIMARY KEY,
    uploaded_by     INTEGER NOT NULL REFERENCES users(id),
    jenis           TEXT NOT NULL,          -- 'soal' | 'materi'
    file_type       TEXT NOT NULL,          -- 'foto' | 'pdf' | 'docx'
    file_id_tg      TEXT NOT NULL,          -- Telegram file_id
    raw_text        TEXT,                   -- hasil ekstraksi
    klasifikasi_ai  JSONB,                  -- {mapel, part, tipe_sumber, confidence, potongan:[...]}
    tipe_sumber     TEXT,                   -- 'per_part' | 'ujian_full' (hasil verifikasi admin)
    status          TEXT NOT NULL DEFAULT 'extracting',
                    -- 'extracting' | 'menunggu_admin' | 'diproses' | 'selesai' | 'ditolak'
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- BANK SOAL (soal asli hasil verifikasi)
CREATE TABLE soal (
    id              SERIAL PRIMARY KEY,
    kode            TEXT UNIQUE NOT NULL,   -- misal 'PM-B9-000123'
    part_id         INTEGER NOT NULL REFERENCES part(id),
    intake_id       INTEGER REFERENCES intake(id),
    teks_soal       TEXT NOT NULL,
    opsi            JSONB,                  -- {"A": "...", "B": "...", ...} null jika isian
    kunci           TEXT,                   -- null sampai admin generate
    pembahasan      TEXT,
    status_kunci    TEXT NOT NULL DEFAULT 'belum',  -- 'belum' | 'draft_ai' | 'verified'
    status          TEXT NOT NULL DEFAULT 'pending',-- 'pending' | 'verified' | 'rejected'
    google_doc_id   TEXT,
    verified_by     INTEGER REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- MATERI
CREATE TABLE materi (
    id              SERIAL PRIMARY KEY,
    kode            TEXT UNIQUE NOT NULL,   -- misal 'MAT-PM-B9-0007'
    part_id         INTEGER NOT NULL REFERENCES part(id),
    intake_id       INTEGER REFERENCES intake(id),
    judul           TEXT NOT NULL,
    konten          TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'pending',
    google_doc_id   TEXT,
    verified_by     INTEGER REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- VARIASI SOAL (yang dikirim ke user, tiap variasi punya kode sendiri)
CREATE TABLE variasi (
    id              SERIAL PRIMARY KEY,
    kode            TEXT UNIQUE NOT NULL,   -- misal 'PM-B9-000123-V04'
    soal_id         INTEGER NOT NULL REFERENCES soal(id),
    teks_soal       TEXT NOT NULL,
    opsi            JSONB,
    kunci           TEXT,                   -- null, diisi saat admin trigger
    pembahasan      TEXT,
    status_kunci    TEXT NOT NULL DEFAULT 'belum',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- PAKET PDF YANG DIKIRIM KE USER
CREATE TABLE paket (
    id              SERIAL PRIMARY KEY,
    kode            TEXT UNIQUE NOT NULL,   -- misal 'PKT-20260904-X7K2'
    user_id         INTEGER NOT NULL REFERENCES users(id),
    part_id         INTEGER NOT NULL REFERENCES part(id),
    jumlah_soal     INTEGER NOT NULL,
    variasi_ids     JSONB NOT NULL,         -- [12, 15, 18, ...]
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_soal_part ON soal(part_id) WHERE status = 'verified';
CREATE INDEX idx_variasi_soal ON variasi(soal_id);
CREATE INDEX idx_intake_status ON intake(status);
CREATE INDEX idx_users_status ON users(status);

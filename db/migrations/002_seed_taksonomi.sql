-- ============================================
-- 002_seed_taksonomi.sql
-- Seed mapel + part, mengikuti daftar isi buku referensi
-- ============================================

INSERT INTO mapel (kode, nama, urutan) VALUES
('PU',  'Penalaran Umum',                  1),
('PK',  'Pengetahuan Kuantitatif',         2),
('PM',  'Penalaran Matematika',            3),
('PPU', 'Pengetahuan dan Pemahaman Umum',  4),
('PBM', 'Pemahaman Bacaan dan Menulis',    5),
('LBI', 'Literasi dalam Bahasa Indonesia', 6),
('LBE', 'Literasi dalam Bahasa Inggris',   7);

-- PU
INSERT INTO part (mapel_id, kode, nama, urutan)
SELECT id, v.kode, v.nama, v.urutan FROM mapel, (VALUES
    ('B1',  'Penalaran Deduktif',    1),
    ('B2',  'Penalaran Induktif',    2),
    ('B3',  'Penalaran Kuantitatif', 3),
    ('SIM', 'Simulasi Soal',         99)
) AS v(kode, nama, urutan) WHERE mapel.kode = 'PU';

-- PK
INSERT INTO part (mapel_id, kode, nama, urutan)
SELECT id, v.kode, v.nama, v.urutan FROM mapel, (VALUES
    ('B1',  'Eksponen dan Bentuk Akar',          1),
    ('B2',  'Logaritma',                         2),
    ('B3',  'Fungsi dan Persamaan Kuadrat',      3),
    ('B4',  'Pengukuran dan Geometri',           4),
    ('B5',  'Fungsi Komposisi dan Inversi',      5),
    ('B6',  'Sistem Persamaan',                  6),
    ('B7',  'Program Linier dan Matriks',        7),
    ('B8',  'Barisan dan Deret',                 8),
    ('B9',  'Statistika',                        9),
    ('B10', 'Permutasi, Kombinasi dan Peluang', 10),
    ('B11', 'Barisan Angka dan Huruf',          11),
    ('B12', 'Aljabar dan Fungsi',               12),
    ('SIM', 'Simulasi Soal',                    99)
) AS v(kode, nama, urutan) WHERE mapel.kode = 'PK';

-- PM
INSERT INTO part (mapel_id, kode, nama, urutan)
SELECT id, v.kode, v.nama, v.urutan FROM mapel, (VALUES
    ('B1',  'Konsep Kesebangunan',               1),
    ('B2',  'Pemodelan Masalah',                 2),
    ('B3',  'Aplikasi Konsep Geometri',          3),
    ('B4',  'Teknik Menemukan Pola dan Bilangan',4),
    ('B5',  'Penambahan Situasi Matematika',     5),
    ('B6',  'Teknik Mendata',                    6),
    ('B7',  'Persamaan dan Pertidaksamaan',      7),
    ('B8',  'Statistika Deskriptif',             8),
    ('B9',  'Teori Peluang',                     9),
    ('SIM', 'Simulasi Soal',                    99)
) AS v(kode, nama, urutan) WHERE mapel.kode = 'PM';

-- PPU (Semantik = SEM, Sintaksis = SIN)
INSERT INTO part (mapel_id, kode, nama, urutan)
SELECT id, v.kode, v.nama, v.urutan FROM mapel, (VALUES
    ('SEM1', 'Semantik: Makna Kata dan Relasi Makna',      1),
    ('SEM2', 'Semantik: Perubahan Makna dan Majas',        2),
    ('SEM3', 'Semantik: Bentuk Dasar dan Bentukan Kata',   3),
    ('SEM4', 'Semantik: Kata Ulang dan Kata Majemuk',      4),
    ('SEM5', 'Semantik: Diksi (Pilihan Kata)',             5),
    ('SEM6', 'Semantik: Hiponim dan Hipernim',             6),
    ('SEM7', 'Semantik: Ungkapan (Idiom)',                 7),
    ('SEM8', 'Semantik: Kata Rujukan',                     8),
    ('SIN1', 'Sintaksis: Frasa dan Klausa',                9),
    ('SIN2', 'Sintaksis: Kalimat',                        10),
    ('SIN3', 'Sintaksis: Kesesuaian Wacana, Hubungan Antarparagraf dan Gagasan Pokok', 11),
    ('SIM',  'Simulasi Soal',                             99)
) AS v(kode, nama, urutan) WHERE mapel.kode = 'PPU';

-- PBM (Ejaan = EYD, Kalimat Efektif = KE)
INSERT INTO part (mapel_id, kode, nama, urutan)
SELECT id, v.kode, v.nama, v.urutan FROM mapel, (VALUES
    ('EYD1', 'Ejaan: Huruf Kapital dan Huruf Miring',        1),
    ('EYD2', 'Ejaan: Penyukuan Kata dan Penulisan Kata',     2),
    ('EYD3', 'Ejaan: Penggunaan Tanda Baca dan Kutipan',     3),
    ('EYD4', 'Ejaan: Kata Baku dan Kata Tidak Baku',         4),
    ('EYD5', 'Ejaan: Catatan Kaki dan Daftar Pustaka',       5),
    ('KE1',  'Kalimat Efektif dan Perbaikannya',             6),
    ('KE2',  'Pemahaman dan Kepaduan Bacaan',                7),
    ('KE3',  'Melengkapi Kalimat',                           8),
    ('SIM',  'Simulasi Soal',                               99)
) AS v(kode, nama, urutan) WHERE mapel.kode = 'PBM';

-- LBI
INSERT INTO part (mapel_id, kode, nama, urutan)
SELECT id, v.kode, v.nama, v.urutan FROM mapel, (VALUES
    ('B1',  'Ide Pokok Paragraf',                            1),
    ('B2',  'Jenis Paragraf',                                2),
    ('B3',  'Pola Pengembangan Paragraf',                    3),
    ('B4',  'Kalimat Utama dan Kalimat Penjelas',            4),
    ('B5',  'Teks Sastra (Tema, Simpulan Isi, Pesan/Amanat)',5),
    ('B6',  'Memahami Isi Teks dan Perbandingan Isi Teks',   6),
    ('SIM', 'Simulasi Soal',                                99)
) AS v(kode, nama, urutan) WHERE mapel.kode = 'LBI';

-- LBE
INSERT INTO part (mapel_id, kode, nama, urutan)
SELECT id, v.kode, v.nama, v.urutan FROM mapel, (VALUES
    ('B1',  'Understanding Main Idea and Topic',              1),
    ('B2',  'Purpose of the Text',                            2),
    ('B3',  'Inference',                                      3),
    ('B4',  'Detailed Information and Stated-Unstated Question', 4),
    ('B5',  'Attitude Expressed',                             5),
    ('B6',  'Vocabulary (Synonym, Reference, Following/Preceding Text)', 6),
    ('B7',  'Cloze Test',                                     7),
    ('B8',  'Organizing Idea (Paraphrasing, Summarizing)',    8),
    ('B9',  'Comparison Two Text',                            9),
    ('SIM', 'Simulasi Soal',                                 99)
) AS v(kode, nama, urutan) WHERE mapel.kode = 'LBE';

import secrets
import string
from datetime import date


def kode_soal(mapel_kode: str, part_kode: str, seq: int) -> str:
    """PM-B9-000123"""
    return f"{mapel_kode}-{part_kode}-{seq:06d}"


def kode_materi(mapel_kode: str, part_kode: str, seq: int) -> str:
    """MAT-PM-B9-0007"""
    return f"MAT-{mapel_kode}-{part_kode}-{seq:04d}"


def kode_variasi(kode_soal_asli: str, n: int) -> str:
    """PM-B9-000123-V04"""
    return f"{kode_soal_asli}-V{n:02d}"


def kode_paket(tgl: date | None = None) -> str:
    """PKT-20260904-X7K2"""
    tgl = tgl or date.today()
    rand = "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(4))
    return f"PKT-{tgl:%Y%m%d}-{rand}"

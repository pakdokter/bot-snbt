"""Arsip soal/materi ke Google Docs (satu dokumen per mapel-part-jenis).

Butuh service account: set env GOOGLE_CREDS_JSON berisi seluruh isi file
JSON kredensial service account (bukan path file). Share folder Drive
tempat dokumen dibuat ke email service account itu kalau ingin admin bisa
lihat dari akun Google pribadi, atau biarkan saja karena bot juga bisa
kirim link dokumennya langsung ke chat.
"""

import json

from google.oauth2 import service_account
from googleapiclient.discovery import build

from config import GOOGLE_CREDS_JSON

SCOPES = [
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive.file",
]

_docs = None
_drive = None


def _client():
    global _docs, _drive
    if _docs is None:
        info = json.loads(GOOGLE_CREDS_JSON)
        creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
        _docs = build("docs", "v1", credentials=creds)
        _drive = build("drive", "v3", credentials=creds)
    return _docs, _drive


def get_or_create_doc(part_row: dict, jenis: str) -> str:
    """Cari dokumen untuk (mapel, part, jenis) ini, buat baru kalau belum ada."""
    docs, drive = _client()
    judul = f"Bank {'Soal' if jenis == 'soal' else 'Materi'} - {part_row['mapel_nama']} - {part_row['nama']}"
    hasil = drive.files().list(
        q=(f"name = '{judul}' and mimeType = 'application/vnd.google-apps.document' "
           "and trashed = false"),
        fields="files(id,name)",
    ).execute()
    files = hasil.get("files", [])
    if files:
        return files[0]["id"]
    doc = docs.documents().create(body={"title": judul}).execute()
    return doc["documentId"]


def append_text(document_id: str, teks: str):
    docs, _ = _client()
    doc = docs.documents().get(documentId=document_id).execute()
    end_index = doc["body"]["content"][-1]["endIndex"] - 1
    docs.documents().batchUpdate(
        documentId=document_id,
        body={"requests": [{
            "insertText": {
                "location": {"index": end_index},
                "text": teks.rstrip() + "\n\n---\n\n",
            }
        }]},
    ).execute()

"""
backend/services/drive_downloader.py
Downloads all notes PDFs from ritnotebook Drive folders using a service account.
Run standalone: python services/drive_downloader.py
"""

import io
import json
import time
from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

# ── CONFIG ────────────────────────────────────────────────────────────────────
CREDENTIALS_FILE = Path("credentials.json")
OUTPUT_DIR       = Path("notes_raw")
SCOPES           = ["https://www.googleapis.com/auth/drive.readonly"]

# CSE-AIML 1st year folders from ritnotebook.pages.dev/notes/first.html
SUBJECT_FOLDERS = {
    "Mathematics_PhysicsCycle":      "1tBGTOy3OYG3MZKsc9qonxmQTws4WTK6_",
    "Physics":                       "14ZLhu4G2KB6vY1T68NCcjSXBJHFYtazR",
    "Communication_English":         "1vA_LTTV7vTXLYor31-5LMzX7Rnkvwdfp",
    "Kannada_Kali_Manasu":           "1q1xubLhJVdeSTTqJH9y70F6O1Yx45Eyg",
    "Scientific_Approach_to_Health": "1r6awFQINcGiwt4ZBvTWMZjTxoRmn4qcy",
    "Principles_of_Programming_C":   "1V9vDDmV3qLyFggmTvHQEEoE7rcKmES02",
    "Mathematics_ChemistryCycle":    "10neY4vTk5WYWfFwiwy7CQXrcz7WJXm8d",
    "Chemistry":                     "166-4ZRAy__G7_0-dNjxrYM_1cCmkZkIJ",
    "Professional_Writing_English":  "1Eh6B7NoiM2cNn69z56EJXWN-s04w-oe1",
    "Constitution_of_India":         "1TD-LUsVS16Ry_-H6lQNyRQS1pRnepRv-",
    "Design_Thinking":               "1vcxv4xmglhkSAIZtTzElGfz78_gjmtNg",
    "CAED":                          "105AA3TJrM60rKkWWlUJJudfCeQLtWkYX",
    "ESC":                           "1x8GwDxOmfOo2iyE7nnYdu9KqOQDFO0B0",
    "ETC":                           "1mF2M2f9Kw2l6H2l7KVl9KRa-QJJ3z-O9",
    "PLC":                           "1iZESy8SPtUsZlu64PR46tyb2xNKNHhJz",
}

# ── AUTH ──────────────────────────────────────────────────────────────────────

def get_drive_service():
    creds = service_account.Credentials.from_service_account_file(
        str(CREDENTIALS_FILE), scopes=SCOPES
    )
    return build("drive", "v3", credentials=creds)


# ── LIST FILES IN FOLDER ──────────────────────────────────────────────────────

def list_files_in_folder(service, folder_id: str) -> list[dict]:
    """List all PDF files (recursively) inside a Drive folder."""
    results = []
    page_token = None

    while True:
        query = (
            f"'{folder_id}' in parents "
            f"and mimeType='application/pdf' "
            f"and trashed=false"
        )
        resp = service.files().list(
            q=query,
            fields="nextPageToken, files(id, name, size)",
            pageToken=page_token,
            pageSize=100,
        ).execute()

        results.extend(resp.get("files", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break

    # Also check sub-folders recursively
    sub_query = (
        f"'{folder_id}' in parents "
        f"and mimeType='application/vnd.google-apps.folder' "
        f"and trashed=false"
    )
    sub_resp = service.files().list(
        q=sub_query,
        fields="files(id, name)",
        pageSize=50,
    ).execute()

    for sub in sub_resp.get("files", []):
        results.extend(list_files_in_folder(service, sub["id"]))

    return results


# ── DOWNLOAD FILE ─────────────────────────────────────────────────────────────

def download_file(service, file_id: str, dest: Path) -> bool:
    if dest.exists():
        print(f"  [SKIP]  {dest.name}")
        return False
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        request = service.files().get_media(fileId=file_id)
        buf = io.BytesIO()
        downloader = MediaIoBaseDownload(buf, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        dest.write_bytes(buf.getvalue())
        kb = dest.stat().st_size // 1024
        print(f"  [OK]    {dest.name} ({kb} KB)")
        return True
    except Exception as e:
        print(f"  [ERROR] {dest.name}: {e}")
        return False


# ── MAIN ──────────────────────────────────────────────────────────────────────

def download_all(output_dir: Path = OUTPUT_DIR) -> list[dict]:
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = []

    print("🔑 Authenticating with service account...")
    try:
        service = get_drive_service()
        print("✅ Authenticated\n")
    except Exception as e:
        print(f"❌ Auth failed: {e}")
        print("Make sure credentials.json is in the backend/ folder")
        return []

    for subject, folder_id in SUBJECT_FOLDERS.items():
        print(f"\n📂 {subject}")
        print(f"   Folder ID: {folder_id}")

        try:
            files = list_files_in_folder(service, folder_id)
        except Exception as e:
            print(f"  [ERROR] Could not list folder: {e}")
            print(f"  ⚠️  Share this folder with your service account email!")
            continue

        if not files:
            print(f"  [WARN]  No PDFs found — folder may not be shared with service account")
            continue

        print(f"  → {len(files)} PDF(s) found")
        subj_dir = output_dir / subject
        subj_dir.mkdir(parents=True, exist_ok=True)

        for f in files:
            dest = subj_dir / f["name"]
            ok = download_file(service, f["id"], dest)
            time.sleep(0.5 if ok else 0.1)
            manifest.append({
                "subject":  subject.replace("_", " "),
                "unit":     "General",
                "filename": f["name"],
                "path":     str(dest.resolve()),
                "file_id":  f["id"],
                "type":     "notes",
            })

    manifest_path = output_dir / "manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"\n✅ Done! {len(manifest)} files. Manifest → {manifest_path}")
    return manifest


if __name__ == "__main__":
    download_all()

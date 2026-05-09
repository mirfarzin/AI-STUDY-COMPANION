import sys
sys.path.insert(0, '.')
from services.pdf_service import ingest_pdf
import json

with open('notes_raw/manifest.json') as f:
    manifest = json.load(f)

for entry in manifest:
    try:
        ingest_pdf(
            pdf_path=entry['path'],
            subject=entry['subject'],
            unit=entry['unit'],
            doc_type='notes',
            force=True
        )
    except Exception as e:
        print(f"ERROR: {entry['filename']}: {e}")

print("ALL DONE")
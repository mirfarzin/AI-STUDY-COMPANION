import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Force UTF-8 stdout so Kannada/non-Latin filenames don't crash on Windows
try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

# Load env variables (must be done before importing services)
load_dotenv()

from services.pdf_service import ingest_folder
from services.qdrant_service import get_collection_stats

def main():
    notes_dir = Path("notes_raw")
    if not notes_dir.exists():
        print(f"Error: {notes_dir.absolute()} not found.")
        sys.exit(1)

    print(f"Starting batch ingestion from {notes_dir.absolute()}...")
    
    # Run the ingestion using the existing folder batch function
    # It reads manifest.json if present, or uses folder names as subjects
    result = ingest_folder(notes_dir)
    
    print("\n--- INGESTION SUMMARY ---")
    print(f"Files Processed: {result['files_processed']}")
    print(f"Chunks Added:    {result['total_chunks']}")
    
    if result["errors"]:
        print(f"\nErrors encountered ({len(result['errors'])}):")
        for err in result["errors"]:
            print(f"  - {err['file']}: {err['error']}")

    print("\n--- QDRANT VALIDATION ---")
    stats = get_collection_stats()
    subjects = stats.get("subjects", [])
    
    from services.qdrant_service import get_all_chunks, query_chunks
    print(f"{'Subject':<35} | {'Chunks':<8} | {'QueryOK'}")
    print("-" * 65)
    for sub in subjects:
        # Get count of chunks for this subject
        # Note: get_all_chunks fetches all, so we use a faster test if possible,
        # but let's just use query_chunks to test OK and fetch first 5.
        try:
            results = query_chunks("test query", n=1, where={"subject": {"$eq": sub}})
            query_ok = "YES" if results is not None else "NO"
            # It's hard to get exact count per subject without scrolling everything, 
            # so we just mark it OK and show total at the end.
            # But wait, Qdrant allows filter counting if we use the client directly.
            from services.qdrant_service import get_qdrant_client, COLLECTION_NAME, Filter, FieldCondition, MatchValue
            client = get_qdrant_client()
            count = client.count(
                collection_name=COLLECTION_NAME, 
                count_filter=Filter(must=[FieldCondition(key="subject", match=MatchValue(value=sub))])
            ).count
            print(f"{sub:<35} | {count:<8} | {query_ok}")
        except Exception as e:
            print(f"{sub:<35} | {'ERR':<8} | NO ({e})")
            
    print("-" * 65)
    print(f"Total Subjects Indexed: {len(subjects)}")
    print(f"Total Chunks in DB: {stats.get('total_chunks', 0)}")
    
    if len(subjects) < 14:
        print(f"\n[WARNING] Only {len(subjects)} subjects found in Qdrant! Expected 14.")
    else:
        print(f"\n[SUCCESS] All 14+ subjects verified in Qdrant.")

if __name__ == "__main__":
    main()

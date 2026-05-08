"""
backend/services/scraper_service.py
Scrapes notes PDFs from ritnotebook.pages.dev for VTU CSE-AIML 1st year.
Targets: /notes/first.html
Run standalone:  python services/scraper_service.py
"""

import re
import time
import json
import httpx
from pathlib import Path
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

BASE_URL      = "https://ritnotebook.pages.dev"
FIRST_YEAR    = "https://ritnotebook.pages.dev/notes/first.html"
OUTPUT_DIR    = Path("notes_raw")
REQUEST_DELAY = 1.5
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

def slugify(text):
    return re.sub(r"[^\w\-]", "_", text.strip()).strip("_")

def get_soup(client, url):
    try:
        r = client.get(url, headers=HEADERS, timeout=20, follow_redirects=True)
        r.raise_for_status()
        return BeautifulSoup(r.text, "html.parser")
    except Exception as e:
        print(f"  [ERROR] {url} → {e}")
        return None

def infer_unit(text):
    m = re.search(r"unit[\s\-_]*(\d)", text, re.IGNORECASE)
    if m: return f"Unit {m.group(1)}"
    m = re.search(r"module[\s\-_]*(\d)", text, re.IGNORECASE)
    if m: return f"Module {m.group(1)}"
    return "General"

def gdrive_to_direct(url):
    m = re.search(r"/file/d/([^/]+)", url)
    if m: return f"https://drive.google.com/uc?export=download&id={m.group(1)}"
    m = re.search(r"id=([^&]+)", url)
    if m: return f"https://drive.google.com/uc?export=download&id={m.group(1)}"
    return None

def download_pdf(client, pdf_url, dest):
    if dest.exists():
        print(f"  [SKIP]  {dest.name}")
        return False
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        with client.stream("GET", pdf_url, headers=HEADERS, timeout=60, follow_redirects=True) as r:
            r.raise_for_status()
            if "html" in r.headers.get("content-type", ""):
                print(f"  [WARN]  HTML response (Drive auth wall): {dest.name}")
                return False
            with open(dest, "wb") as f:
                for chunk in r.iter_bytes(8192):
                    f.write(chunk)
        kb = dest.stat().st_size // 1024
        if kb < 5:
            print(f"  [WARN]  Too small ({kb}KB): {dest.name}")
            dest.unlink()
            return False
        print(f"  [OK]    {dest.name} ({kb} KB)")
        return True
    except Exception as e:
        print(f"  [ERROR] {e}")
        return False

def collect_pdfs(soup, page_url):
    pdfs = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(strip=True) or "notes"
        full = urljoin(page_url, href)
        if href.lower().endswith(".pdf"):
            pdfs.append({"name": text, "url": full, "unit": infer_unit(text)})
        elif "drive.google.com" in href:
            dl = gdrive_to_direct(href)
            if dl:
                pdfs.append({"name": text, "url": dl, "unit": infer_unit(text)})
    return pdfs

def scrape_ritnotebook(output_dir=OUTPUT_DIR):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = []

    with httpx.Client() as client:
        print(f"\n🔍 Fetching: {FIRST_YEAR}")
        soup = get_soup(client, FIRST_YEAR)
        if not soup:
            print("❌ Could not load first.html")
            return []

        # Print all links so we can see the real structure
        print("\n📋 All links on first.html:")
        for a in soup.find_all("a", href=True):
            print(f"   {a.get_text(strip=True)[:50]:<50} → {a['href']}")

        subjects = {}
        current = "General"

        for tag in soup.find_all(["h1","h2","h3","h4","h5","b","strong","p","li","a","div","td","th"]):
            text = tag.get_text(strip=True)

            # Treat headings/bold as subject name
            if tag.name in ["h1","h2","h3","h4","h5"] and 3 < len(text) < 80:
                current = text
                subjects.setdefault(current, [])

            elif tag.name == "a" and tag.get("href"):
                href = tag["href"]
                full = urljoin(FIRST_YEAR, href)

                if href.lower().endswith(".pdf"):
                    subjects.setdefault(current, []).append(
                        {"name": text, "url": full, "unit": infer_unit(text)})

                elif "drive.google.com" in href:
                    dl = gdrive_to_direct(href)
                    if dl:
                        subjects.setdefault(current, []).append(
                            {"name": text, "url": dl, "unit": infer_unit(text)})

                # Follow sub-html pages on same domain
                elif href.endswith(".html") and urlparse(full).netloc == urlparse(BASE_URL).netloc and full != FIRST_YEAR:
                    print(f"\n  📄 Sub-page: {full}")
                    time.sleep(REQUEST_DELAY)
                    sub = get_soup(client, full)
                    if sub:
                        sub_pdfs = collect_pdfs(sub, full)
                        print(f"     → {len(sub_pdfs)} PDFs")
                        subjects.setdefault(current, []).extend(sub_pdfs)

        print(f"\n📚 Subjects: {list(subjects.keys())}")

        for subject, pdfs in subjects.items():
            if not pdfs:
                continue
            print(f"\n📖 {subject} — {len(pdfs)} file(s)")
            subj_dir = output_dir / slugify(subject)
            subj_dir.mkdir(parents=True, exist_ok=True)
            seen = set()

            for i, pdf in enumerate(pdfs):
                if pdf["url"] in seen:
                    continue
                seen.add(pdf["url"])
                safe = re.sub(r"[^\w\-\.]", "_", pdf["name"])[:80]
                if not safe.endswith(".pdf"):
                    safe += f"_{i+1}.pdf"
                dest = subj_dir / safe
                print(f"  ⬇  {pdf['unit']} | {safe[:55]}")
                ok = download_pdf(client, pdf["url"], dest)
                time.sleep(REQUEST_DELAY if ok else 0.3)
                manifest.append({
                    "subject": subject, "unit": pdf["unit"],
                    "filename": safe, "path": str(dest.resolve()),
                    "url": pdf["url"], "type": "notes",
                })

    with open(output_dir / "manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"\n✅ Done! {len(manifest)} entries.")
    return manifest

if __name__ == "__main__":
    scrape_ritnotebook()
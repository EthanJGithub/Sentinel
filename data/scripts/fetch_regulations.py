"""
Fetch the primary regulatory source documents to the D: cache (C: is tight).

What it pulls:
  - CMS State Operations Manual, Appendix PP (LTC surveyor guidance, F-tags)  [PDF]
  - 42 CFR Part 483 Subpart B (eCFR)                                          [HTML/XML]
  - A pointer file for NFPA 101 (2012) — the code is copyrighted; we cache the
    public CMS K-tag crosswalk reference, not the licensed NFPA text.

The committed RAG corpus (data/regulations/regulations.jsonl) is a curated,
verified subset so the demo runs fully offline. This script exists so the
"real data, cached to D:" pipeline is genuinely wired and re-runnable.

Usage:  python data/scripts/fetch_regulations.py
Cache:  D:\\sentinel-data\\regulations\\
"""
import os
import sys
import urllib.request
from pathlib import Path

CACHE = Path(os.environ.get("SENTINEL_DATA_DIR", r"D:\sentinel-data")) / "regulations"

SOURCES = {
    # CMS SOM Appendix PP (LTC). CMS occasionally revises the path; update if 404.
    "cms_appendix_pp.pdf":
        "https://www.cms.gov/Medicare/Provider-Enrollment-and-Certification/GuidanceforLawsAndRegulations/Downloads/Appendix-PP-State-Operations-Manual.pdf",
    # eCFR XML for 42 CFR 483 (authoritative, machine-readable)
    "ecfr_42cfr483.xml":
        "https://www.ecfr.gov/api/versioner/v1/full/2024-01-01/title-42.xml?part=483",
}

NFPA_NOTE = """NFPA 101 (2012 ed.) is copyrighted and not redistributed here.
CMS adopts it via 42 CFR 483.90(a). For survey, the public crosswalk is the
CMS Life Safety Code (K-tag) survey resources. The committed corpus paraphrases
NFPA provisions as references and points back to 42 CFR 483.90(a).
Public reference index: https://www.cms.gov/medicare/provider-enrollment-and-certification/certificationandcomplianc/lsc
"""


def fetch(name: str, url: str) -> None:
    dest = CACHE / name
    if dest.exists() and dest.stat().st_size > 0:
        print(f"[cache] {name} already present ({dest.stat().st_size:,} bytes)")
        return
    print(f"[get]   {name} <- {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "Sentinel-Demo/1.0 (portfolio)"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r, open(dest, "wb") as f:
            f.write(r.read())
        print(f"[ok]    {name} ({dest.stat().st_size:,} bytes)")
    except Exception as e:  # noqa: BLE001 - best-effort downloader
        print(f"[warn]  could not fetch {name}: {e}")
        print("         The committed corpus still runs the demo offline.")


def main() -> int:
    CACHE.mkdir(parents=True, exist_ok=True)
    print(f"Caching regulatory sources to: {CACHE}")
    for name, url in SOURCES.items():
        fetch(name, url)
    (CACHE / "NFPA101_NOTE.txt").write_text(NFPA_NOTE, encoding="utf-8")
    print("Done. Curated corpus is data/regulations/regulations.jsonl (verified subset).")
    return 0


if __name__ == "__main__":
    sys.exit(main())

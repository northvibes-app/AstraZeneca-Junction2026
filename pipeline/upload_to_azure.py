"""Upload the pipeline's results to the team's Azure Blob Storage container.

Run on its own:        python3 pipeline/upload_to_azure.py
Or after the pipeline: python3 pipeline/run_pipeline.py --upload

The access link (a SAS URL) is a secret: anyone who has it can write to the
container. It must never be committed to git. It is read from
  1. the environment variable AZURE_BLOB_SAS_URL, or
  2. the line after "Blob SAS URL" in a local data.txt in the repository root.
     data.txt is listed in .gitignore and stays on your machine.
This script never prints the link.

What is uploaded is listed in pipeline/config.json under "upload". The fact sheets
(output/facts/*.md) come first: a document search reads short texts well and rows
of numbers badly. Each file is stored as <container>/pipeline-output/<path> and
replaces the previous upload of the same name. Only the standard library is used.
"""
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "pipeline" / "output"
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CONFIG      # noqa: E402

PREFIX = CONFIG["upload"]["prefix"]


def files_to_upload():
    """Expand the patterns from config.json into paths relative to pipeline/output."""
    found = []
    for pattern in CONFIG["upload"]["files"]:
        matches = sorted(OUT.glob(pattern))
        found += [m.relative_to(OUT).as_posix() for m in matches] or [pattern]
    return found


def read_sas_url():
    url = os.environ.get("AZURE_BLOB_SAS_URL", "").strip()
    if not url and (ROOT / "data.txt").exists():
        lines = [line.strip() for line in (ROOT / "data.txt").read_text(encoding="utf-8").splitlines()]
        for i, line in enumerate(lines):
            if line.lower() == "blob sas url" and i + 1 < len(lines):
                url = lines[i + 1]
    if not url.startswith("https://") or "?" not in url:
        sys.exit("No Azure access link found. Set the environment variable AZURE_BLOB_SAS_URL.")
    return url


def describe(error):
    """Error text without the query string, so the secret never reaches the console."""
    body = error.read().decode("utf-8", "replace")
    code = body.split("<Code>")[1].split("</Code>")[0] if "<Code>" in body else ""
    return f"HTTP {error.code} {code}".strip()


def upload():
    base, sas = read_sas_url().split("?", 1)
    parts = urllib.parse.urlsplit(base)
    print(f"Target: {parts.netloc}{parts.path}/{PREFIX}")

    names, failed = files_to_upload(), 0
    for name in names:
        path = OUT / name
        if not path.exists():
            print(f"  skipped  {name} (not found; run the pipeline first)")
            failed += 1
            continue
        data = path.read_bytes()
        request = urllib.request.Request(
            f"{base}/{PREFIX}{urllib.parse.quote(name)}?{sas}", data=data, method="PUT",
            headers={"x-ms-blob-type": "BlockBlob",
                     "Content-Type": ("text/markdown" if name.endswith(".md") else "text/csv")
                     + "; charset=utf-8"})
        try:
            with urllib.request.urlopen(request, timeout=120):
                print(f"  uploaded {name} ({len(data) / 1024:,.0f} KB)")
        except urllib.error.HTTPError as error:
            print(f"  FAILED   {name}: {describe(error)}")
            failed += 1
        except urllib.error.URLError as error:
            print(f"  FAILED   {name}: {error.reason}")
            failed += 1

    # Read the container listing back, to confirm what is actually stored there.
    try:
        listing = urllib.request.Request(
            f"{base}?restype=container&comp=list&prefix={urllib.parse.quote(PREFIX)}&{sas}")
        with urllib.request.urlopen(listing, timeout=60) as response:
            blobs = ET.fromstring(response.read()).iter("Blob")
            stored = {b.findtext("Name"): b.findtext("Properties/Content-Length") for b in blobs}
        print(f"Stored under {PREFIX}: {len(stored)} files, {len(names)} of them from this upload")
        for name in names:
            size = stored.get(PREFIX + name)
            local = (OUT / name).stat().st_size if (OUT / name).exists() else None
            state = "missing" if size is None else "ok" if int(size) == local else "SIZE DIFFERS"
            print(f"  {state:12} {name}")
            failed += state not in ("ok",)
    except urllib.error.HTTPError as error:
        print(f"Could not list the container to verify: {describe(error)}")
    return failed == 0


if __name__ == "__main__":
    sys.exit(0 if upload() else 1)

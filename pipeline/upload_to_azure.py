"""Upload the pipeline's CSV results to the team's Azure Blob Storage container.

Run on its own:        python3 pipeline/upload_to_azure.py
Or after the pipeline: python3 pipeline/run_pipeline.py --upload

Where the access link comes from, first match wins:
  1. the environment variable AZURE_BLOB_SAS_URL
  2. the line after "Blob SAS URL" in data.txt in the repository root

The link is a secret: anyone who has it can write to the container. This script
never prints it. Prefer the environment variable and keep the link out of git.

Each file is stored as  <container>/pipeline-output/<file name>  and replaces the
previous upload of the same name. Only the Python standard library is used.
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
PREFIX = "pipeline-output/"

# The readable results. The 8 MB clean layer (observations_clean.csv.gz) is left out:
# it is compressed, and everything needed for analysis is in the files below.
FILES = ["equity_gaps.csv", "region_profile.csv", "region_factor_levels.csv",
         "observations_by_factor.csv", "observations_analysis.csv", "data_gaps.csv",
         "quarantine.csv"]


def read_sas_url():
    url = os.environ.get("AZURE_BLOB_SAS_URL", "").strip()
    if not url and (ROOT / "data.txt").exists():
        lines = [line.strip() for line in (ROOT / "data.txt").read_text(encoding="utf-8").splitlines()]
        for i, line in enumerate(lines):
            if line.lower() == "blob sas url" and i + 1 < len(lines):
                url = lines[i + 1]
    if not url.startswith("https://") or "?" not in url:
        sys.exit("No Azure access link found. Set AZURE_BLOB_SAS_URL or add it to data.txt.")
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

    failed = 0
    for name in FILES:
        path = OUT / name
        if not path.exists():
            print(f"  skipped  {name} (not found; run the pipeline first)")
            failed += 1
            continue
        data = path.read_bytes()
        request = urllib.request.Request(
            f"{base}/{PREFIX}{urllib.parse.quote(name)}?{sas}", data=data, method="PUT",
            headers={"x-ms-blob-type": "BlockBlob", "Content-Type": "text/csv; charset=utf-8"})
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
        print(f"Stored under {PREFIX}: {len(stored)} files")
        for name in FILES:
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

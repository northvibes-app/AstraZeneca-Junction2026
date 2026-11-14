"""Small download helper shared by the fetch scripts.

Adds what a one-line urlopen lacks: a user agent the public APIs accept, retries
with a growing pause for temporary network or server errors, and a record of
what was downloaded so the next run can tell whether a source has changed.
"""
import hashlib
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

USER_AGENT = "curl/8.0"      # Sotkanet rejects Python's default user agent
RETRIES = 4


def download(url, timeout=120):
    """Return the response body as bytes. Retries on network errors and HTTP 5xx / 429."""
    last_error = None
    for attempt in range(RETRIES):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read()
        except urllib.error.HTTPError as error:
            if error.code < 500 and error.code != 429:
                raise                                   # a 4xx will not fix itself
            last_error = error
        except (urllib.error.URLError, TimeoutError, ConnectionError) as error:
            last_error = error
        pause = 2 ** attempt                            # 1, 2, 4, 8 seconds
        print(f"    retry in {pause} s ({last_error})")
        time.sleep(pause)
    raise RuntimeError(f"Download failed after {RETRIES} attempts: {last_error}")


def get_json(url, timeout=120):
    return json.loads(download(url, timeout))


class ChangeLog:
    """Remembers a checksum per downloaded item and reports what changed since last time."""

    def __init__(self, path):
        self.path = Path(path)
        self.previous = json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else {}
        self.current = {}

    def record(self, name, payload: bytes):
        digest = hashlib.sha256(payload).hexdigest()
        self.current[name] = digest
        before = self.previous.get(name)
        return "new" if before is None else "unchanged" if before == digest else "CHANGED"

    def save(self):
        self.path.write_text(json.dumps(self.current, indent=1, sort_keys=True), encoding="utf-8")

"""Send the decision-tree questions to the team's RAG API, one request per question.

This does for every entry in questions.json what api-query.txt does for one question.

    python3 decision_tree/ask.py                          # ask every question
    python3 decision_tree/ask.py screening_inequalities   # ask only the named ones

Each answer is saved as decision_tree/responses/<id>.json. A short summary is printed:
the status, how many documents the search found, and whether the answer looks cut off.

The API answers "503 Service Unavailable" when it receives questions too quickly, so
the script pauses between questions and tries a refused question again after a wait.
Only the Python standard library is used.
"""
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "responses"
PAUSE_SECONDS = 5            # between two questions
RETRY_WAITS = [20, 40, 60]   # seconds to wait before each further attempt after a 503


def ask(endpoint, question, top_k):
    body = json.dumps({"question": question, "topK": top_k}).encode("utf-8")
    request = urllib.request.Request(
        endpoint, data=body, method="POST",
        headers={"Content-Type": "application/json", "User-Agent": "curl/8.0"})
    for wait in RETRY_WAITS + [None]:
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            if error.code not in (429, 503) or wait is None:
                raise
            time.sleep(wait)


def main():
    config = json.loads((HERE / "questions.json").read_text(encoding="utf-8"))
    wanted = set(sys.argv[1:])
    ids = [q["id"] for q in config["questions"]]
    if len(ids) != len(set(ids)):
        sys.exit("questions.json: every id must be unique.")
    unknown = wanted - set(ids)
    if unknown:
        sys.exit(f"No question with id: {', '.join(sorted(unknown))}")

    OUT.mkdir(exist_ok=True)
    failed = 0
    for entry in config["questions"]:
        if wanted and entry["id"] not in wanted:
            continue
        try:
            result = ask(config["endpoint"], entry["question"], entry.get("topK", config["topK"]))
        except (urllib.error.URLError, ValueError) as error:
            print(f"FAILED  {entry['id']}: {error}")
            failed += 1
            continue
        finally:
            time.sleep(PAUSE_SECONDS)
        (OUT / f"{entry['id']}.json").write_text(
            json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        answer = (result.get("answer") or "").rstrip()
        cut_off = bool(answer) and answer[-1] not in ".!?)*"
        sources = ", ".join(s.get("blobPath", "?") for s in result.get("sources", []))
        print(f"{result.get('status', '?'):10} {entry['id']}: "
              f"{result.get('retrieval', {}).get('documentsFound', '?')} documents"
              f"{', answer cut off' if cut_off else ''}  [{sources}]")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()

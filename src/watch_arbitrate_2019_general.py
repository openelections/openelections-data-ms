"""Watch the 2019 general OCR batch and arbitrate each county as it
completes: run arbitrate_2019_general.py --fix on every newly completed
county (the arbiter only proposes fixes gated on the recap's printed TOTAL
reconciling to the county CSV), then re-run the crosscheck. Output is
appended to /tmp/gen_arb.log so every proposal stays reviewable.

Usage: uv run python watch_arbitrate_2019_general.py  (Ctrl+C to stop)
"""

import subprocess
import sys
import time
from pathlib import Path

DONE = [c.lower() for c in (
    "Adams", "Alcorn", "Amite", "Attala", "Bolivar", "Chickasaw", "Clarke",
    "Coahoma", "Copiah", "Covington", "DeSoto", "Forrest", "George",
    "Grenada", "Hancock", "Harrison", "Hinds", "Holmes", "Jackson", "Jasper",
    "Jones", "Lamar", "Lauderdale", "Lawrence", "Leake", "Lee", "Lowndes",
    "Madison", "Montgomery", "Neshoba", "Newton", "Oktibbeha", "Pearl River",
    "Pike", "Pontotoc", "Rankin", "Smith", "Stone", "Warren", "Winston",
    "Yazoo")]


def completed():
    out = []
    for c in DONE:
        marker = Path(f"cache/2019-general-{c.replace(' ', '_')}/paddle"
                      "/.complete")
        if marker.exists():
            out.append(c)
    return out


def main():
    seen = set(completed())
    print(f"start: {len(seen)} already complete: {sorted(seen)}",
          flush=True)
    while len(seen) < len(DONE):
        time.sleep(30)
        new = [c for c in completed() if c not in seen]
        for c in new:
            seen.add(c)
            print(f"\n######## arbitrating {c}", flush=True)
            subprocess.run(
                [sys.executable, "arbitrate_2019_general.py", "--fix", c],
                stdout=sys.stdout, stderr=sys.stderr)
            subprocess.run([sys.executable, "crosscheck_2019_general.py"],
                           stdout=sys.stdout, stderr=sys.stdout)
    print("\nall counties arbitrated", flush=True)


if __name__ == "__main__":
    main()
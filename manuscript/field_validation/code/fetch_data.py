"""Download the pinned SolarMagix v2 inputs and verify their byte counts and hashes."""

import argparse
import hashlib
import json
import shutil
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen


def verify(path, spec):
    if not path.exists() or path.stat().st_size != spec["size"]:
        return False
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest() == spec["sha256_hash"]


def fetch(destination, sources):
    destination.mkdir(parents=True, exist_ok=True)
    for name, spec in sources["files"].items():
        target = destination / name
        if not verify(target, spec):
            temporary = target.with_suffix(".part")
            for attempt in range(3):
                try:
                    request = Request(spec["download_url"], headers={"User-Agent": "Mozilla/5.0"})
                    with urlopen(request, timeout=90) as response, temporary.open("wb") as out:
                        shutil.copyfileobj(response, out)
                    if not verify(temporary, spec):
                        raise ValueError(f"SolarMagix digest mismatch for {name}")
                    temporary.replace(target)
                    break
                except (OSError, URLError, ValueError):
                    temporary.unlink(missing_ok=True)
                    if attempt == 2:
                        raise
                    time.sleep(2 ** attempt)
        print(f"Verified {name}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path("data"))
    args = parser.parse_args()
    manifest = Path(__file__).with_name("sources.json")
    fetch(args.data, json.loads(manifest.read_text()))

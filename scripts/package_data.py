"""Create reproducible compressed snapshots and a complete acquisition manifest."""
from pathlib import Path
import gzip
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
LARGE = ["europe_plant_inventory.csv", "era5_daily_pilot.csv", "cmip6_daily_pilot.csv"]


def main():
    compressed = []
    for name in LARGE:
        path = ROOT / "data/processed" / name
        if path.exists():
            target = path.with_suffix(path.suffix + ".gz")
            target.write_bytes(gzip.compress(path.read_bytes(), mtime=0))
            compressed.append(dict(path=str(target.relative_to(ROOT)),
                                   uncompressed_bytes=path.stat().st_size, compressed_bytes=target.stat().st_size))
    requests = []
    for p in sorted((ROOT / "data/raw").rglob("*.source.json")):
        record = json.loads(p.read_text())
        record["cache_path"] = str(p.relative_to(ROOT)).removesuffix(".source.json")
        requests.append(record)
    files = []
    for p in sorted((ROOT / "data/processed").glob("*")):
        if p.is_file() and p.name != "era5_daily_with_thresholds.csv":
            files.append(dict(path=str(p.relative_to(ROOT)), bytes=p.stat().st_size,
                              sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
    manifest = dict(requests=requests, processed_files=files, compressed_snapshots=compressed,
                    provenance_note="Raw responses are cached locally. Public snapshots preserve the downloaded values; no synthetic replacement of missing data.")
    (ROOT / "data/provenance/download_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Packaged {len(compressed)} datasets; {len(requests)} source requests with SHA-256")


if __name__ == "__main__":
    main()

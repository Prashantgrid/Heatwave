"""Restore plain CSVs from the small, versioned gzip snapshots, without network."""
from pathlib import Path
import gzip

root = Path(__file__).resolve().parents[1]
for path in sorted((root / "data/processed").glob("*.csv.gz")):
    target = path.with_suffix("")
    target.write_bytes(gzip.decompress(path.read_bytes()))
    print(target.relative_to(root))

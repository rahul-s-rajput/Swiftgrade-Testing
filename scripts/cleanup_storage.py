"""Find and delete Storage files that no `image` row references.

Deleting database rows never removes Storage files, so earlier session deletes and
duplicate uploads left orphans behind. Every assessment's images are referenced from
`image.url`, so nothing an assessment uses is touched.

Usage (repo root, .venv active):
    python scripts/cleanup_storage.py                 # dry run: report only
    python scripts/cleanup_storage.py --delete        # actually delete orphans
    python scripts/cleanup_storage.py --env PATH      # use a specific .env

By default the .env is taken from the desktop app's data dir
(%APPDATA%/com.swiftgrade.testing.assistant/.env), falling back to ./.env.
"""
import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
LIST_PAGE = 1000


def _load_env(explicit: str | None) -> Path:
    candidates = [Path(explicit)] if explicit else [
        Path(os.environ.get("APPDATA", "")) / "com.swiftgrade.testing.assistant" / ".env",
        Path(os.environ.get("APPDATA", "")) / "com.markgrading.assistant" / ".env",
        REPO_ROOT / ".env",
    ]
    for p in candidates:
        if p.is_file():
            load_dotenv(p, override=True)
            return p
    sys.exit(f"No .env found (tried: {', '.join(str(c) for c in candidates)})")


def _list_all(bucket_api, prefix: str = ""):
    """Yield (path, size_bytes) for every object under prefix, recursing into folders."""
    offset = 0
    while True:
        items = bucket_api.list(prefix, {"limit": LIST_PAGE, "offset": offset}) or []
        for it in items:
            name = it.get("name")
            if not name:
                continue
            full = f"{prefix}/{name}" if prefix else name
            if it.get("id") is None:  # folders have no id
                yield from _list_all(bucket_api, full)
            else:
                yield full, int((it.get("metadata") or {}).get("size") or 0)
        if len(items) < LIST_PAGE:
            return
        offset += LIST_PAGE


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--delete", action="store_true", help="delete orphaned files (default: dry run)")
    ap.add_argument("--env", help="path to the .env file to use")
    args = ap.parse_args()

    env_path = _load_env(args.env)
    sys.path.insert(0, str(REPO_ROOT))
    from app.supabase_client import supabase
    from app.util.storage import path_from_public_url, remove_objects, storage_bucket

    bucket = storage_bucket()
    print(f"Using {env_path}, bucket '{bucket}'")

    referenced = set()
    start = 0
    while True:
        rows = supabase.table("image").select("url").range(start, start + 999).execute().data or []
        for r in rows:
            p = path_from_public_url(r.get("url") or "", bucket)
            if p:
                referenced.add(p)
        if len(rows) < 1000:
            break
        start += 1000

    objects = list(_list_all(supabase.storage.from_(bucket)))
    orphans = [(p, s) for p, s in objects if p not in referenced]
    total = sum(s for _, s in objects)
    orphan_bytes = sum(s for _, s in orphans)
    missing = referenced - {p for p, _ in objects}

    mb = 1024 * 1024
    print(f"Objects in bucket:      {len(objects)} ({total / mb:.1f} MB)")
    print(f"Referenced by images:   {len(referenced)}")
    print(f"Orphaned (unused):      {len(orphans)} ({orphan_bytes / mb:.1f} MB)")
    if missing:
        print(f"Warning: {len(missing)} image rows point at files that no longer exist")

    if not orphans:
        return
    if not args.delete:
        print("\nDry run - nothing deleted. Re-run with --delete to remove the orphaned files.")
        return

    removed, errors = remove_objects((p for p, _ in orphans), bucket)
    print(f"\nDeleted {removed} files, freed ~{orphan_bytes / mb:.1f} MB")
    for e in errors:
        print(f"  error: {e}")


if __name__ == "__main__":
    main()

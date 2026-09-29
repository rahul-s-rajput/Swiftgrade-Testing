"""Helpers for the Supabase Storage bucket that holds assessment images."""
import logging
import os
from typing import Iterable, List, Optional, Tuple
from urllib.parse import unquote, urlparse

from ..supabase_client import supabase

# Supabase Storage accepts at most this many paths per remove() call in practice;
# keep batches small so one bad path doesn't sink a large delete.
REMOVE_BATCH_SIZE = 100


def storage_bucket() -> str:
    return os.getenv("SUPABASE_STORAGE_BUCKET", "grading-images") or "grading-images"


def path_from_public_url(url: str, bucket: Optional[str] = None) -> Optional[str]:
    """Recover the object path from a public URL stored in `image.url`.

    Public URLs look like {SUPABASE_URL}/storage/v1/object/public/{bucket}/{path}.
    Returns None for data: URLs or URLs that point somewhere else.
    """
    if not url or not isinstance(url, str):
        return None
    bucket = bucket or storage_bucket()
    marker = f"/storage/v1/object/public/{bucket}/"
    path = urlparse(url).path
    idx = path.find(marker)
    if idx == -1:
        return None
    obj = unquote(path[idx + len(marker):])
    return obj or None


def remove_objects(paths: Iterable[str], bucket: Optional[str] = None) -> Tuple[int, List[str]]:
    """Delete objects from the bucket. Returns (removed_count, error_messages)."""
    bucket = bucket or storage_bucket()
    unique = sorted({p for p in paths if p})
    removed = 0
    errors: List[str] = []
    for i in range(0, len(unique), REMOVE_BATCH_SIZE):
        batch = unique[i:i + REMOVE_BATCH_SIZE]
        try:
            res = supabase.storage.from_(bucket).remove(batch)
            removed += len(res or [])
        except Exception as e:
            logging.warning("Storage remove failed for %d paths: %s", len(batch), e)
            errors.append(str(e))
    return removed, errors

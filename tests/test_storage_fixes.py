"""Offline tests for the Supabase storage/DB-size fixes (v1.0.6).

Runs against an in-memory fake of the Supabase client, so no real project, network or
OpenRouter call is involved. Run from the repo root:

    python tests/test_storage_fixes.py
"""
import asyncio
import json
import os
import sys
import tempfile
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

# Fake credentials so importing the app never needs (or touches) the real project.
os.environ["SUPABASE_URL"] = "https://fakeproject.supabase.co"
os.environ["SUPABASE_SERVICE_ROLE_KEY"] = "eyJhbGciOiJIUzI1NiJ9.eyJyb2xlIjoic2VydmljZV9yb2xlIn0.fake"
os.environ["OPENROUTER_API_KEY"] = "fake-openrouter-key"
os.environ["SUPABASE_STORAGE_BUCKET"] = "grading-images"
os.environ["ENV_FILE_PATH"] = str(Path(tempfile.gettempdir()) / "nonexistent-swiftgrade.env")
os.environ["GRADE_LOG_DIR"] = tempfile.mkdtemp(prefix="swiftgrade-test-logs-")

BUCKET = "grading-images"
PUBLIC = f"https://fakeproject.supabase.co/storage/v1/object/public/{BUCKET}/"
CHILD_TABLES = ("image", "question", "result", "rubric_result", "token_usage", "stats")


# ---------------------------------------------------------------------------
# In-memory fake Supabase client
# ---------------------------------------------------------------------------

class _Res:
    def __init__(self, data):
        self.data = data


class _Query:
    def __init__(self, db, table):
        self.db, self.table = db, table
        self.op, self.payload, self.filters, self.on_conflict = "select", None, [], None
        self._range = None

    # builders
    def select(self, *cols, **_):
        self.op = "select"
        return self

    def insert(self, rows):
        self.op, self.payload = "insert", rows
        return self

    def upsert(self, rows, on_conflict=None, **_):
        self.op, self.payload, self.on_conflict = "upsert", rows, on_conflict
        return self

    def update(self, values):
        self.op, self.payload = "update", values
        return self

    def delete(self):
        self.op = "delete"
        return self

    def eq(self, col, val):
        self.filters.append(lambda r: r.get(col) == val)
        return self

    def neq(self, col, val):
        self.filters.append(lambda r: r.get(col) != val)
        return self

    def in_(self, col, vals):
        vals = list(vals)
        self.filters.append(lambda r: r.get(col) in vals)
        return self

    def like(self, col, pattern):
        prefix = pattern.rstrip("%")
        self.filters.append(lambda r: str(r.get(col, "")).startswith(prefix))
        return self

    def order(self, *_, **__):
        return self

    def limit(self, *_):
        return self

    def range(self, a, b):
        self._range = (a, b)
        return self

    def _match(self, r):
        return all(f(r) for f in self.filters)

    def execute(self):
        self.db.calls.append((self.table, self.op))
        if self.db.fail_tables.get(self.table):
            raise RuntimeError(f"simulated failure on {self.table}")
        rows = self.db.tables.setdefault(self.table, [])
        if self.op == "select":
            out = [dict(r) for r in rows if self._match(r)]
            if self._range:
                out = out[self._range[0]:self._range[1] + 1]
            return _Res(out)
        if self.op in ("insert", "upsert"):
            new = self.payload if isinstance(self.payload, list) else [self.payload]
            keys = [k.strip() for k in (self.on_conflict or "").split(",") if k.strip()]
            for n in new:
                if keys:
                    for i, r in enumerate(rows):
                        if all(r.get(k) == n.get(k) for k in keys):
                            rows[i] = dict(n)
                            break
                    else:
                        rows.append(dict(n))
                else:
                    rows.append(dict(n))
            return _Res(new)
        if self.op == "update":
            hit = [r for r in rows if self._match(r)]
            for r in hit:
                r.update(self.payload)
            return _Res(hit)
        if self.op == "delete":
            gone = [r for r in rows if self._match(r)]
            self.db.tables[self.table] = [r for r in rows if not self._match(r)]
            if self.table == "session":  # ON DELETE CASCADE
                ids = {r["id"] for r in gone}
                for t in CHILD_TABLES:
                    self.db.tables[t] = [r for r in self.db.tables.get(t, []) if r.get("session_id") not in ids]
            return _Res(gone)
        raise AssertionError(self.op)


class _Bucket:
    def __init__(self, db):
        self.db = db

    def list(self, folder=None, options=None):
        options = options or {}
        if self.db.fail_storage_list:
            raise RuntimeError("simulated list failure")
        folder = (folder or "").strip("/")
        names, folders = [], set()
        for path, size in self.db.objects.items():
            if folder and not path.startswith(folder + "/"):
                continue
            rest = path[len(folder) + 1:] if folder else path
            if "/" in rest:
                folders.add(rest.split("/", 1)[0])
            else:
                names.append({"name": rest, "id": "obj-" + rest, "metadata": {"size": size}})
        items = [{"name": f, "id": None, "metadata": None} for f in sorted(folders)] + sorted(names, key=lambda x: x["name"])
        search = options.get("search")
        if search:
            items = [i for i in items if i["name"].startswith(search)]
        offset, limit = options.get("offset", 0), options.get("limit", 100)
        return items[offset:offset + limit]

    def remove(self, paths):
        if self.db.fail_storage_remove:
            raise RuntimeError("simulated remove failure")
        self.db.removed_batches.append(list(paths))
        gone = [p for p in paths if p in self.db.objects]
        for p in gone:
            del self.db.objects[p]
        return [{"name": p} for p in gone]

    def create_signed_upload_url(self, path):
        self.db.signed_paths.append(path)
        return {"signed_url": f"https://fakeproject.supabase.co/storage/v1/object/upload/sign/{BUCKET}/{path}?token=t", "token": "t", "path": path}

    def get_public_url(self, path):
        return PUBLIC + path


class _Storage:
    def __init__(self, db):
        self.db = db

    def from_(self, bucket):
        assert bucket == BUCKET, bucket
        return _Bucket(self.db)


class _Rpc:
    def __init__(self, db, name):
        self.db, self.name = db, name

    def execute(self):
        if self.name not in self.db.rpcs:
            raise RuntimeError(f"function public.{self.name}() does not exist")
        return _Res(self.db.rpcs[self.name])


class FakeSupabase:
    def __init__(self):
        self.tables = {}
        self.objects = {}  # storage path -> size
        self.rpcs = {}
        self.calls, self.removed_batches, self.signed_paths = [], [], []
        self.fail_tables = {}
        self.fail_storage_list = self.fail_storage_remove = False
        self.storage = _Storage(self)

    def table(self, name):
        return _Query(self, name)

    def rpc(self, name, params=None):
        return _Rpc(self, name)


# ---------------------------------------------------------------------------
# App wiring
# ---------------------------------------------------------------------------

import logging  # noqa: E402

logging.disable(logging.CRITICAL)  # the app logs full bodies at INFO; keep test output readable

from fastapi.testclient import TestClient  # noqa: E402

import app.main as app_main  # noqa: E402
import app.routers.grade as grade  # noqa: E402
import app.routers.images as images  # noqa: E402
import app.routers.sessions as sessions  # noqa: E402
import app.routers.usage as usage  # noqa: E402
import app.util.storage as storage_util  # noqa: E402

# load_environment() may have pulled a real .env from the repo root; force fakes back.
os.environ["SUPABASE_URL"] = "https://fakeproject.supabase.co"
os.environ["SUPABASE_STORAGE_BUCKET"] = BUCKET

PATCHED_MODULES = [grade, images, sessions, usage, storage_util]


def fresh_db() -> FakeSupabase:
    db = FakeSupabase()
    for m in PATCHED_MODULES:
        m.supabase = db
    return db


client = TestClient(app_main.app)
H1, H2 = "a" * 64, "b" * 64


# ---------------------------------------------------------------------------
# Tests: upload paths (content-addressed, dedupe)
# ---------------------------------------------------------------------------

def test_signed_url_new_content_gets_hash_path():
    db = fresh_db()
    r = client.post("/images/signed-url", json={"filename": "Page 1 (scan).JPG", "content_type": "image/jpeg", "content_hash": H1, "role": "student"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["path"] == f"student/{H1}.jpg", body
    assert body["exists"] is False
    assert body["uploadUrl"], "upload URL expected for new content"
    assert body["publicUrl"] == PUBLIC + f"student/{H1}.jpg"
    assert db.signed_paths == [f"student/{H1}.jpg"]


def test_signed_url_existing_content_skips_upload():
    db = fresh_db()
    db.objects[f"student/{H1}.jpg"] = 1234
    r = client.post("/images/signed-url", json={"filename": "copy.jpg", "content_type": "image/jpeg", "content_hash": H1, "role": "student"})
    body = r.json()
    assert r.status_code == 200 and body["exists"] is True, body
    assert body["publicUrl"] == PUBLIC + f"student/{H1}.jpg"
    assert db.signed_paths == [], "must not create an upload URL for existing content"


def test_signed_url_same_content_different_role_is_separate_object():
    db = fresh_db()
    db.objects[f"student/{H1}.jpg"] = 1234
    body = client.post("/images/signed-url", json={"filename": "p.jpg", "content_type": "image/jpeg", "content_hash": H1, "role": "grading_rubric"}).json()
    assert body["path"] == f"grading_rubric/{H1}.jpg" and body["exists"] is False, body


def test_signed_url_search_prefix_is_not_mistaken_for_match():
    # Storage `search` is a prefix match; a different extension must not count as existing.
    db = fresh_db()
    db.objects[f"student/{H1}.png"] = 10
    body = client.post("/images/signed-url", json={"filename": "p.jpg", "content_type": "image/jpeg", "content_hash": H1, "role": "student"}).json()
    assert body["exists"] is False, body


def test_signed_url_existence_check_failure_falls_back_to_upload():
    db = fresh_db()
    db.fail_storage_list = True
    body = client.post("/images/signed-url", json={"filename": "p.jpg", "content_type": "image/jpeg", "content_hash": H1, "role": "student"}).json()
    assert body["exists"] is False and body["uploadUrl"], body


def test_signed_url_legacy_request_still_works():
    db = fresh_db()
    body = client.post("/images/signed-url", json={"filename": "old client.png", "content_type": "image/png"}).json()
    folder, name = body["path"].split("/", 1)
    assert len(folder) == 32 and name == "old-client.png", body
    assert body["exists"] is False


def test_signed_url_rejects_bad_hash_and_role():
    fresh_db()
    r1 = client.post("/images/signed-url", json={"filename": "p.jpg", "content_type": "image/jpeg", "content_hash": "not-a-hash"})
    r2 = client.post("/images/signed-url", json={"filename": "p.jpg", "content_type": "image/jpeg", "content_hash": H1, "role": "hacker"})
    r3 = client.post("/images/signed-url", json={"filename": "../x.jpg", "content_type": "image/jpeg", "content_hash": H1})
    assert r1.status_code == 422 and r2.status_code == 422 and r3.status_code == 400, (r1.status_code, r2.status_code, r3.status_code)


def test_same_url_registers_for_two_sessions():
    db = fresh_db()
    url = PUBLIC + f"student/{H1}.jpg"
    db.tables["session"] = [{"id": "s1"}, {"id": "s2"}]
    for sid in ("s1", "s2"):
        r = client.post("/images/register", json={"session_id": sid, "role": "student", "url": url, "order_index": 0})
        assert r.status_code == 200, r.text
    assert len(db.tables["image"]) == 2


# ---------------------------------------------------------------------------
# Tests: session delete removes files it alone uses
# ---------------------------------------------------------------------------

def _seed_two_sessions(db):
    shared = PUBLIC + f"student/{H1}.jpg"
    only_s1 = PUBLIC + f"answer_key/{H2}.jpg"
    legacy = PUBLIC + "0123456789abcdef0123456789abcdef/Kin%20AK%20(1).png"
    db.tables["session"] = [{"id": "s1"}, {"id": "s2"}]
    db.tables["image"] = [
        {"session_id": "s1", "role": "student", "url": shared, "order_index": 0},
        {"session_id": "s1", "role": "answer_key", "url": only_s1, "order_index": 0},
        {"session_id": "s1", "role": "grading_rubric", "url": legacy, "order_index": 0},
        {"session_id": "s2", "role": "student", "url": shared, "order_index": 0},
    ]
    db.tables["result"] = [{"session_id": "s1", "question_id": "Q1"}, {"session_id": "s2", "question_id": "Q1"}]
    db.objects = {
        f"student/{H1}.jpg": 100,
        f"answer_key/{H2}.jpg": 200,
        "0123456789abcdef0123456789abcdef/Kin AK (1).png": 300,
        "unrelated/other.jpg": 400,
    }


def test_delete_session_removes_only_unshared_files():
    db = fresh_db()
    _seed_two_sessions(db)
    r = client.delete("/sessions/s1")
    assert r.status_code == 204, r.text
    assert sorted(db.objects) == sorted([f"student/{H1}.jpg", "unrelated/other.jpg"]), db.objects
    assert [row["session_id"] for row in db.tables["image"]] == ["s2"]
    assert [row["session_id"] for row in db.tables["result"]] == ["s2"]


def test_delete_last_session_using_shared_file_removes_it():
    db = fresh_db()
    _seed_two_sessions(db)
    client.delete("/sessions/s1")
    client.delete("/sessions/s2")
    assert sorted(db.objects) == ["unrelated/other.jpg"], db.objects


def test_delete_session_survives_storage_failure():
    db = fresh_db()
    _seed_two_sessions(db)
    db.fail_storage_remove = True
    r = client.delete("/sessions/s1")
    assert r.status_code == 204, r.text
    assert [s["id"] for s in db.tables["session"]] == ["s2"], "rows must still be deleted"


def test_delete_missing_session_is_idempotent():
    db = fresh_db()
    r = client.delete("/sessions/does-not-exist")
    assert r.status_code == 204 and not db.removed_batches


def test_path_from_public_url():
    f = storage_util.path_from_public_url
    assert f(PUBLIC + "abc/Kin%20AK%20(1).png") == "abc/Kin AK (1).png"
    assert f(PUBLIC + f"student/{H1}.jpg?download=1") == f"student/{H1}.jpg"
    assert f("data:image/png;base64,AAAA") is None
    assert f("https://elsewhere.com/x.jpg") is None
    assert f("https://fakeproject.supabase.co/storage/v1/object/public/other-bucket/x.jpg") is None
    assert f("") is None and f(None) is None


# ---------------------------------------------------------------------------
# Tests: /usage
# ---------------------------------------------------------------------------

def test_usage_without_migration_reports_unavailable():
    fresh_db()
    body = client.get("/usage").json()
    assert body["available"] is False and "006" in body["message"], body


def test_usage_reports_restricted_project():
    db = fresh_db()

    class _Restricted:
        def execute(self):
            raise RuntimeError("{'message': 'Service for this project is restricted due to the following "
                               "violations: exceed_storage_size_quota.'}")

    db.rpc = lambda name, params=None: _Restricted()
    body = client.get("/usage").json()
    assert body["available"] is False and body["restricted"] is True, body
    assert "restricted" in body["message"], body


def test_usage_percentages_and_limits():
    db = fresh_db()
    db.rpcs["get_usage_stats"] = {"db_bytes": 400 * 1024 * 1024, "storage_bytes": 256 * 1024 * 1024, "storage_objects": 42}
    body = client.get("/usage").json()
    assert body["available"] is True and body["warn_percent"] == 80
    assert body["database"]["percent"] == 80.0, body
    assert body["storage"]["percent"] == 25.0 and body["storage"]["objects"] == 42, body


def test_usage_limit_env_override():
    db = fresh_db()
    db.rpcs["get_usage_stats"] = {"db_bytes": 4 * 1024 ** 3, "storage_bytes": 0, "storage_objects": 0}
    os.environ["SUPABASE_DB_LIMIT_MB"] = str(8 * 1024)
    try:
        body = client.get("/usage").json()
    finally:
        del os.environ["SUPABASE_DB_LIMIT_MB"]
    assert body["database"]["percent"] == 50.0, body


# ---------------------------------------------------------------------------
# Tests: grading no longer stores full responses
# ---------------------------------------------------------------------------

ENCRYPTED = "E" * 40_000  # stands in for reasoning.encrypted blobs


def _response(content: str, usage=None):
    return {
        "id": "gen-123",
        "model": "anthropic/claude-test",
        "provider": "Anthropic",
        "usage": usage or {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150, "cost": 0.0123},
        "choices": [{
            "finish_reason": "stop",
            "native_finish_reason": "end_turn",
            "message": {
                "role": "assistant",
                "content": content,
                "reasoning": "long visible reasoning " * 200,
                "reasoning_details": [{"type": "reasoning.encrypted", "data": ENCRYPTED}],
            },
        }],
    }


RUBRIC_JSON = json.dumps({"grading_criteria": [{"question_number": "Q1", "components": []}, {"question_number": "Q2", "components": []}]})
GOOD_ANSWERS = json.dumps({"result": [{"first_name": "A", "last_name": "B", "answers": [
    {"question_number": "Q1", "marks_awarded": 2, "rubric_notes": "ok"},
    {"question_number": "Q2", "marks_awarded": 1, "rubric_notes": "partial"},
]}]})


def _seed_grading(db):
    db.tables["session"] = [{"id": "g1", "status": "created", "selected_rubric_template": "default", "selected_assessment_template": "default"}]
    db.tables["image"] = [
        {"session_id": "g1", "role": "student", "url": PUBLIC + f"student/{H1}.jpg", "order_index": 0},
        {"session_id": "g1", "role": "grading_rubric", "url": PUBLIC + f"grading_rubric/{H1}.jpg", "order_index": 0},
    ]
    db.tables["question"] = [
        {"session_id": "g1", "question_id": "Q1", "number": 1, "max_marks": 2},
        {"session_id": "g1", "question_id": "Q2", "number": 2, "max_marks": 2},
    ]


def _run_grading(db, assessment_content):
    async def fake_openrouter(client_, model, messages, reasoning=None, session_id=None, try_index=None, instance_id=None, *a, **k):
        return _response(RUBRIC_JSON if model == "rubric/model" else assessment_content)

    original = grade._call_openrouter
    grade._call_openrouter = fake_openrouter
    try:
        r = client.post("/grade/single", json={
            "session_id": "g1",
            "default_tries": 2,
            "model_pairs": [{"rubric_model": {"name": "rubric/model"}, "assessment_model": {"name": "assess/model"}}],
        })
    finally:
        grade._call_openrouter = original
    return r


def test_grading_result_rows_have_no_raw_output():
    db = fresh_db()
    _seed_grading(db)
    r = _run_grading(db, GOOD_ANSWERS)
    assert r.status_code == 200, r.text
    rows = db.tables["result"]
    assert len(rows) == 4, rows  # 2 questions x 2 tries
    assert all(row["raw_output"] is None for row in rows), "per-question rows must not store the response"
    assert {row["marks_awarded"] for row in rows} == {2, 1}
    assert db.tables["session"][0]["status"] == "graded"


def test_rubric_result_is_slim_and_keeps_criteria():
    db = fresh_db()
    _seed_grading(db)
    _run_grading(db, GOOD_ANSWERS)
    rubric_rows = db.tables["rubric_result"]
    assert len(rubric_rows) == 2
    for row in rubric_rows:
        raw = json.dumps(row["raw_output"])
        assert ENCRYPTED not in raw and "reasoning_details" not in raw and "long visible reasoning" not in raw
        assert len(raw) < 1000, len(raw)
        assert json.loads(row["rubric_response"])["grading_criteria"], "rubric text must still be saved"
        assert row["raw_output"]["choices"][0]["message"]["content"] == RUBRIC_JSON


def test_token_usage_still_recorded_for_both_phases():
    db = fresh_db()
    _seed_grading(db)
    _run_grading(db, GOOD_ANSWERS)
    phases = sorted((t["phase"], t["try_index"]) for t in db.tables["token_usage"])
    assert phases == [("assessment", 1), ("assessment", 2), ("rubric", 1), ("rubric", 2)], phases
    assert all(t["total_tokens"] == 150 for t in db.tables["token_usage"])


def test_parse_error_row_keeps_slim_copy_for_debugging():
    db = fresh_db()
    _seed_grading(db)
    _run_grading(db, "the model rambled and returned no JSON")
    rows = [r for r in db.tables["result"] if r["question_id"] == "__parse_error__"]
    assert len(rows) == 2, db.tables["result"]
    for row in rows:
        raw = json.dumps(row["raw_output"])
        assert ENCRYPTED not in raw and len(raw) < 1000
        assert row["raw_output"]["choices"][0]["message"]["content"].startswith("the model rambled")
        assert row["validation_errors"]


def test_full_response_still_in_local_session_log():
    db = fresh_db()
    _seed_grading(db)
    # The real _call_openrouter writes the log; exercise the logger it uses directly.
    grade._append_session_log("g1", "RESPONSE " + json.dumps(_response("x")))
    log = Path(grade.GRADE_LOG_DIR) / "session_g1.log"
    assert log.is_file() and ENCRYPTED in log.read_text(encoding="utf-8")


def test_slim_response_edge_cases():
    s = grade._slim_response
    assert s(None) is None and s("text") is None and s([1]) is None
    assert s({"error": {"message": "boom"}}) == {"error": {"message": "boom"}}
    assert s({"id": "x", "choices": []}) == {"id": "x"}
    slim = s(_response("c"))
    assert slim["usage"]["cost"] == 0.0123 and slim["provider"] == "Anthropic"
    assert len(json.dumps(slim)) < 500


# ---------------------------------------------------------------------------
# Tests: cleanup_storage.py
# ---------------------------------------------------------------------------

def test_cleanup_script_lists_nested_objects_and_finds_orphans():
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    import cleanup_storage

    db = fresh_db()
    _seed_two_sessions(db)
    db.objects["deep/nested/folder/x.jpg"] = 5
    found = dict(cleanup_storage._list_all(db.storage.from_(BUCKET)))
    assert found == db.objects, found

    referenced = {storage_util.path_from_public_url(r["url"]) for r in db.tables["image"]}
    orphans = sorted(p for p in found if p not in referenced)
    assert orphans == ["deep/nested/folder/x.jpg", "unrelated/other.jpg"], orphans


def test_cleanup_script_paginates_large_folders():
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    import cleanup_storage

    db = fresh_db()
    for i in range(2500):
        db.objects[f"bulk/{i:05d}.jpg"] = 1
    found = list(cleanup_storage._list_all(db.storage.from_(BUCKET)))
    assert len(found) == 2500 and len({p for p, _ in found}) == 2500


def test_remove_objects_batches_and_dedupes():
    db = fresh_db()
    for i in range(250):
        db.objects[f"x/{i}.jpg"] = 1
    removed, errors = storage_util.remove_objects([f"x/{i}.jpg" for i in range(250)] + ["x/0.jpg", None, ""])
    assert removed == 250 and not errors
    assert [len(b) for b in db.removed_batches] == [100, 100, 50]


# ---------------------------------------------------------------------------

def main() -> int:
    tests = [(n, f) for n, f in globals().items() if n.startswith("test_") and callable(f)]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"PASS  {name}")
        except Exception:
            failed += 1
            print(f"FAIL  {name}")
            traceback.print_exc()
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

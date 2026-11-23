"""Run read-only observations inserted into temporary copies of pinned upstream tests."""

from contextlib import closing
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
from tempfile import NamedTemporaryFile, TemporaryDirectory

COMMIT = "ee5fe34e136488a1839ac73bcca8321c51a31b75"
BUN_VERSION = "1.4.4"
PREFIX = "LEARN_STORAGE_OBSERVATION "
ANSI = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")

BUS_OBSERVE = '''      console.log("LEARN_STORAGE_OBSERVATION " + JSON.stringify({
        phase: "__PHASE__",
        projection: yield* db.all("SELECT value FROM event_commit_probe"),
        event: yield* db.select({ type: EventTable.type, seq: EventTable.seq })
          .from(EventTable).where(eq(EventTable.aggregate_id, aggregateID)).all(),
        event_sequence: yield* db.select({ seq: EventSequenceTable.seq })
          .from(EventSequenceTable).where(eq(EventSequenceTable.aggregate_id, aggregateID)).all(),
      }))
'''

PROMPT_OBSERVE = '''      const observe = (phase: string) => Effect.gen(function* () {
        console.log("LEARN_STORAGE_OBSERVATION " + JSON.stringify({
          phase,
          session_inbox: yield* db.select({
            id: SessionInboxTable.id, delivery: SessionInboxTable.delivery, enqueued_seq: SessionInboxTable.enqueued_seq,
          }).from(SessionInboxTable).where(eq(SessionInboxTable.session_id, sessionID)).all(),
          session_message: yield* db.select({
            id: SessionMessageTable.id, type: SessionMessageTable.type, seq: SessionMessageTable.seq,
          }).from(SessionMessageTable).where(eq(SessionMessageTable.session_id, sessionID)).all(),
          event: yield* db.select({ type: EventTable.type, seq: EventTable.seq })
            .from(EventTable).where(eq(EventTable.aggregate_id, sessionID)).orderBy(EventTable.seq).all(),
        }))
      })
'''

RECOVERY_OBSERVE = '''      const observe = (phase: string, drains: ReadonlyArray<string> = []) => Effect.gen(function* () {
        console.log("LEARN_STORAGE_OBSERVATION " + JSON.stringify({
          phase,
          session_v2: yield* database.db.select({
            id: SessionTable.id, claimed_at: SessionTable.time_suspended, attempts: SessionTable.resume_attempts,
          }).from(SessionTable).where(eq(SessionTable.id, child)).all(),
          job: yield* database.db.select({
            kind: JobTable.kind, status: JobTable.status, notification_id: JobTable.notification_id,
          }).from(JobTable).where(eq(JobTable.child_session_id, child)).all(),
          parent_inbox: yield* database.db.select({
            id: SessionInboxTable.id, type: SessionInboxTable.type, delivery: SessionInboxTable.delivery,
          }).from(SessionInboxTable).where(eq(SessionInboxTable.session_id, parent)).all(),
          drains,
        }))
      })
'''

def insert_before(source, target, insertion):
    if source.count(target) != 1:
        raise ValueError(f"Expected one source anchor: {target}")
    return source.replace(target, insertion + target, 1)

def patch_bus(source):
    failed = '      expect(String(exit)).toContain("commit failed")'
    no_payload = '      expect(event.durable?.seq).toBe(Event.Seq.make(0))\n      expect(yield* db.all("SELECT value FROM event_commit_probe"))'
    return insert_before(insert_before(source, failed, BUS_OBSERVE.replace("__PHASE__", "rollback")),
                         no_payload, BUS_OBSERVE.replace("__PHASE__", "persist_false"))

def patch_prompt(source):
    source = source.replace("import { SessionTable } from", "import { SessionInboxTable, SessionMessageTable, SessionTable } from", 1)
    target = "      yield* session.resume(sessionID)"
    return insert_before(source, target, PROMPT_OBSERVE + '      yield* observe("admitted")\n').replace(
        target, target + '\n      yield* observe("run_finished")', 1
    )

def patch_case(source, name, insertion_at, observations):
    begin = source.index(f'  it.effect("{name}"')
    end = source.index("\n  it.effect(", begin + 10)
    case = source[begin:end]
    case = insert_before(case, insertion_at, RECOVERY_OBSERVE + observations[0])
    for target, insertion in observations[1:]:
        case = insert_before(case, target, insertion)
    return source[:begin] + case + source[end:]

def patch_recovery(source):
    # Keep the same upstream test layers and change only the SQLite connection path.
    target = "    LayerNode.group([Database.node, Bus.node, SessionStore.node, SessionInbox.node, Job.node, KV.node, Session.node]),"
    if source.count(target) != 1:
        raise ValueError("Expected the original recovery test layer")
    source = source.replace(target, target + '\n    [Database.node.replace(Database.configured({ path: process.env.LEARN_STORAGE_PROBE_DB! }))],')
    source = patch_case(
        source, "delivers a completed outbox row at boot without touching the child",
        "      const drained: Session.ID[] = []", [
            '      yield* observe("completed_report_before_scan")\n',
            ("      // Replay uses the snapshot", '      yield* observe("completed_report_after_scan", drained)\n'),
        ],
    )
    return patch_case(
        source, "resumes a background subagent and notifies its parent exactly once",
        "      const resumed = yield* Deferred.make<void>()", [
            '      yield* observe("running_child_before_scan")\n',
            ("      expect(yield* attempts(database, child)).toBe(1)",
             '      yield* observe("running_child_after_claim", drained)\n'),
            ("      expect(yield* restarted.pendingBackground).toEqual([])",
             '      yield* observe("running_child_finished", drained)\n'),
        ],
    )

PROBES = {
    "08-events-and-bus": (
        "test/bus.test.ts", "rolls back the durable event and projector when the local commit fails|projects durable events without retaining their payloads",
        patch_bus, 2,
    ),
    "09-projections-storage": (
        "test/session-runner-recorded.test.ts", "executes one recorded prompt", patch_prompt, 2,
    ),
    "10-restart-recovery": (
        "test/session-execution.test.ts",
        "resumes a background subagent and notifies its parent exactly once|delivers a completed outbox row at boot without touching the child",
        patch_recovery, 5,
    ),
}

def verified_runtime(path):
    checkout = Path(path).expanduser().resolve()
    actual = subprocess.check_output(["git", "-C", str(checkout), "rev-parse", "HEAD"], text=True).strip()
    if actual != COMMIT:
        raise ValueError("请使用课程固定提交的独立 OpenCode 副本")
    bun = shutil.which("bun")
    if not bun or subprocess.check_output([bun, "--version"], text=True).strip() != BUN_VERSION:
        raise ValueError(f"请在 PATH 中使用 Bun {BUN_VERSION}")
    env = dict(os.environ)
    env.pop("RECORD", None)
    env["CI"] = "true"
    env["NO_COLOR"] = "1"
    return checkout, bun, env

def report(command, checkout, bun, env):
    result = subprocess.run([bun, *command], cwd=checkout / "packages/core", env=env,
                            capture_output=True, text=True, timeout=60)
    output = ANSI.sub("", result.stdout + "\n" + result.stderr)
    counts = {key: int(value) for value, key in re.findall(r"(?m)^\s*(\d+) (pass|fail)\b", output)}
    if result.returncode or counts.get("pass", 0) == 0 or counts.get("fail") != 0:
        raise RuntimeError(output[-4500:])
    return counts, output

def reopened_rows(path):
    ids = ("ses_subagent_recovery_child", "ses_outbox_child")
    parents = ("ses_subagent_recovery_parent", "ses_outbox_parent")
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as db:
        db.row_factory = sqlite3.Row
        return {
            "phase": "reopened_sqlite_after_bun_exit",
            "session_v2": [dict(row) for row in db.execute(
                "SELECT id, time_suspended AS claimed_at, resume_attempts AS attempts "
                "FROM session_v2 WHERE id IN (?, ?) ORDER BY id", ids
            )],
            "job": [dict(row) for row in db.execute(
                "SELECT child_session_id, status, kind FROM job WHERE child_session_id IN (?, ?) ORDER BY child_session_id",
                ids
            )],
            "parent_inbox": [dict(row) for row in db.execute(
                "SELECT id, session_id, type, delivery FROM session_inbox WHERE session_id IN (?, ?) ORDER BY session_id",
                parents
            )],
        }

def run_probe(chapter, path):
    checkout, bun, env = verified_runtime(path)
    test, pattern, patch, row_count = PROBES[chapter]
    original = subprocess.check_output(
        ["git", "-C", str(checkout), "show", f"{COMMIT}:packages/core/{test}"], text=True
    )
    with TemporaryDirectory(prefix="learn-opencode-storage-") as directory:
        db_path = Path(directory) / "classroom.db"
        env["LEARN_STORAGE_PROBE_DB"] = str(db_path)
        temporary = None
        try:
            with NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".test.ts", prefix="learn-storage-",
                                   dir=checkout / "packages/core/test", delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(patch(original))
            _, output = report(["run", "test", f"test/{temporary.name}", "--test-name-pattern", pattern],
                               checkout, bun, env)
            rows = [json.loads(line[len(PREFIX):]) for line in output.splitlines() if line.startswith(PREFIX)]
            if len(rows) != row_count:
                raise RuntimeError(f"预期 {row_count} 条数据库快照，实际 {len(rows)} 条\n{output[-4500:]}")
            if chapter == "10-restart-recovery":
                rows.append(reopened_rows(db_path))
            return rows
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

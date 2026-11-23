"""Read actual model requests from temporary copies of pinned original Core tests."""

import json
from pathlib import Path
import subprocess
from tempfile import NamedTemporaryFile

from storage_probe import COMMIT, report, verified_runtime

PREFIX = "LEARN_CONTEXT_OBSERVATION "

def event(payload):
    return '      console.log("LEARN_CONTEXT_OBSERVATION " + JSON.stringify(' + payload + '))\n'

def replace_once(source, old, new):
    if source.count(old) != 1:
        raise ValueError(f"Expected one source anchor: {old}")
    return source.replace(old, new, 1)

def insert_in_case(source, case, anchor, insert):
    start = source.index(case)
    end = source.index(anchor, start)
    return source[:end] + insert + source[end:]

def patch_history(source):
    case = 'it.effect("history never decodes rows before the latest compaction or its kept tail"'
    anchor = '    expect(toLLMMessages(history, resolved.ref)).toEqual(\n'
    observation = event('''{
        phase: "history_window",
        storedMessageIDs: [...earlier, kept, compaction, tail].map((message) => message.id),
        droppedBeforeCut: earlier.map((message) => message.id),
        keepID: kept.id,
        loadedMessageIDs: history.map((message) => message.id),
        modelMessages: toLLMMessages(history, resolved.ref),
      }''')
    return insert_in_case(source, case, anchor, observation)

def patch_budget(source):
    old = '''        .pipe(Effect.map((outcome) => outcome.status !== "skipped"))'''
    new = '''        .pipe(Effect.map((outcome) => {
          console.log("LEARN_CONTEXT_OBSERVATION " + JSON.stringify({
            phase: "auto_gate",
            limit: context.model.limit,
            native: context.model.compaction?.type === "native",
            estimate: estimate ?? SessionCompaction.estimatePrompt(context),
            passedByCaller: estimate !== undefined,
            outcome: outcome.status,
          }))
          return outcome.status !== "skipped"
        }))'''
    return replace_once(source, old, new)

# Replica of the upstream runner scenario's structure. Only the material, test model
# replies and markers are course-specific. SessionRunner and dependencies are original.
PROCUREMENT = r'''  scenario("course context procurement with an early clause and a retained exact quote", function* (s) {
    const earlyQuote = "ANNEX-A §2: quotation must not exceed CNY 100000 before tax."
    const recentQuote = "ANNEX-B §4: submission closes at 17:00 CST on 2026-12-03."
    const earlier = earlyQuote + "\n" + "  Prior pricing working notes and attachments index.\n".repeat(90)
    const recent = recentQuote + "\n" + "  Verify the submission deadline against the addendum.\n".repeat(55)
    yield* s.llm.push(TestLLM.textWithUsage("Earlier procurement notes received.", "course-first", 3_950))
    yield* s.runPrompt(earlier)
    const first = s.requests[0]
    s.currentModel = compactModel
    s.requests.length = 0
    // Deliberately omit the exact ceiling from the scripted summary.
    yield* s.llm.push(
      TestLLM.text("## Objective\n- Verify the revised submission deadline.\n## Relevant Files\n- ANNEX-A §2 contains the old quotation ceiling.", "course-summary"),
      TestLLM.textWithUsage("Reviewed the retained deadline evidence.", "course-answer", 3_950),
    )
    yield* s.runPrompt(recent)
    expect(s.requests).toHaveLength(2)
    expect(JSON.stringify(s.requests[0].messages)).toContain(earlyQuote)
    expect(JSON.stringify(s.requests[0].messages)).toContain(recentQuote)
    const resumed = JSON.stringify(s.requests[1].messages)
    expect(resumed).toContain(recentQuote)
    expect(resumed).not.toContain(earlyQuote)
    expect(resumed).toContain("ANNEX-A §2 contains the old quotation ceiling.")
    const store = yield* SessionStore.Service
    const stored = yield* store.messages({ sessionID, order: "asc" })
    expect(JSON.stringify(stored)).toContain(earlyQuote)
    console.log("LEARN_CONTEXT_OBSERVATION " + JSON.stringify({
      phase: "procurement_evidence",
      teachingFixture: true,
      earlyQuote,
      recentQuote,
      requestLabels: ["original_primary", "summary", "primary_after"],
      requests: [first, ...s.requests].map((request) => ({
        model: request.model.id,
        system: request.system,
        messages: request.messages,
        toolNames: request.tools.map((tool) => tool.name),
        maxOutputTokens: request.maxTokens,
      })),
      stored: stored.map((message) => ({ type: message.type, id: message.id })),
      earlyQuoteStillStored: JSON.stringify(stored).includes(earlyQuote),
    }))
  })
'''

CAPTURE = '''{
        phase: "__PHASE__",
        requests: s.requests.map((request) => ({
          model: request.model.id,
          system: request.system,
          messages: request.messages,
          toolNames: request.tools.map((tool) => tool.name),
          maxOutputTokens: request.maxTokens,
        })),
      }'''

def patch_runner(source):
    auto = '  scenario("automatically compacts into a completed summary and retained recent turn"'
    source = replace_once(source, auto, PROCUREMENT + "\n" + auto)
    source = insert_in_case(source, auto, '    const context = yield* store.context(sessionID)\n',
                            event(CAPTURE.replace("__PHASE__", "long_conversation")))
    overflow = '  scenario("forces one compaction and retries after provider context overflow"'
    return insert_in_case(source, overflow, "    yield* replaySessionProjection(sessionID)",
                          event(CAPTURE.replace("__PHASE__", "provider_overflow")))

def patch_native(source):
    anchor = "          state.calls++\n"
    added = """          if (state.calls <= 2) {
            const body = JSON.parse(await request.clone().text())
            console.log("LEARN_CONTEXT_OBSERVATION " + JSON.stringify({
              phase: "native_wire_request", ordinal: state.calls, request: body,
            }))
          }
"""
    return replace_once(source, anchor, anchor + added)

PROBES = {
    "11-context-history": [
        ("test/session-compaction.test.ts", "history never decodes rows before the latest compaction or its kept tail", patch_history),
    ],
    "12-token-budget": [
        ("test/session-compaction.test.ts", "auto compaction estimates current content against the buffered prompt ceiling", patch_budget),
    ],
    "13-compaction": [
        ("test/session-runner.test.ts",
         "course context procurement|automatically compacts into a completed summary|forces one compaction and retries after provider context overflow",
         patch_runner),
        ("test/session-native-compaction.test.ts", "manual trigger persists and continues, retains earlier users repeatedly", patch_native),
    ],
}

def run_probe(chapter, path):
    checkout, bun, env = verified_runtime(path)
    rows = []
    for test, pattern, patch in PROBES[chapter]:
        original = subprocess.check_output(
            ["git", "-C", str(checkout), "show", f"{COMMIT}:packages/core/{test}"], text=True
        )
        temporary = None
        try:
            with NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".test.ts", prefix="learn-context-",
                                    dir=checkout / "packages/core/test", delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(patch(original))
            _, output = report(["run", "test", f"test/{temporary.name}", "--test-name-pattern", pattern],
                               checkout, bun, env)
            captured = [json.loads(line[len(PREFIX):]) for line in output.splitlines() if line.startswith(PREFIX)]
            if not captured:
                raise RuntimeError(f"原版流程没有输出观测记录。\n{output[-3500:]}")
            if patch is patch_native:
                if [row.get("ordinal") for row in captured] != [1, 2]:
                    raise RuntimeError("预期两份原生协议 HTTP 请求")
                rows.append({"phase": "native_wire", "requests": [row["request"] for row in captured]})
            else:
                rows.extend(captured)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
    return rows

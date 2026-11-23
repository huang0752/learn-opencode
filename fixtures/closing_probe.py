"""Optional reruns of the closing chapter observations from the pinned OpenCode checkout."""

from contextlib import contextmanager
import json
import os
from pathlib import Path
import re
import subprocess
from tempfile import NamedTemporaryFile, TemporaryDirectory

from storage_probe import ANSI, COMMIT, report, verified_runtime

PREFIX = "LEARN_EXTENSION "

@contextmanager
def isolated_env(env):
    with TemporaryDirectory(prefix="learn-opencode-final-") as directory:
        home = Path(directory)
        paths = {"HOME": home, "XDG_CONFIG_HOME": home / "config", "XDG_DATA_HOME": home / "data",
                 "XDG_STATE_HOME": home / "state", "XDG_CACHE_HOME": home / "cache", "TMPDIR": home / "tmp"}
        for target in paths.values():
            target.mkdir(parents=True, exist_ok=True)
        clean = {k: v for k, v in env.items()
                 if not k.startswith(("OPENCODE_", "GIT_CONFIG")) and
                 not re.search(r"(?:^|_)(?:TOKEN|API_KEY|SECRET|PASSWORD|CREDENTIALS?|AUTHORIZATION)$", k, re.I)}
        yield {**clean, **{key: str(value) for key, value in paths.items()}, "NO_COLOR": "1"}

def execute(path, package, args, *, tests=True):
    checkout, bun, env = verified_runtime(path)
    if package == "core" and tests:
        return report(args, checkout, bun, env)[0]
    with isolated_env(env) as clean:
        result = subprocess.run([bun, *args], cwd=checkout / "packages" / package, env=clean,
                                text=True, capture_output=True, timeout=90)
    output = ANSI.sub("", result.stdout + "\n" + result.stderr)
    if result.returncode:
        raise RuntimeError(output[-4500:])
    if not tests:
        return output.strip()
    counts = {key: int(value) for value, key in re.findall(r"(?m)^\s*(\d+) (pass|fail)\b", output)}
    if not counts.get("pass") or counts.get("fail") != 0:
        raise RuntimeError(output[-4500:])
    return counts

def insert_in_case(text, case, marker, extra):
    position = text.index(marker, text.index(case))
    return text[:position] + extra + text[position:]

def run_extension_probe(slug, path):
    data = {
        "14-extensions": [
            ("test/session-skill.test.ts", "materializes mentioned skills on their owning prompt",
             "      expect(yield* sessions.messages({ sessionID: session.id })).toEqual([\n",
             '''      const observed = yield* sessions.messages({ sessionID: session.id })
      console.log("LEARN_EXTENSION " + JSON.stringify({
        phase: "skill_attached_to_prompt",
        messages: observed.filter((message) => message.type === "user").map((message) => ({
          id: message.id,
          skills: message.skills?.map((skill) => ({ id: skill.id, mention: skill.mention, hasContent: !!skill.text })),
        })),
      }))
''')
        ],
        "15-hooks-mcp": [
            ("test/plugin/tool-input-repair-integration.test.ts", "repairs tool input before validating its original schema",
             '    yield* registry.transform((draft) => draft.remove("repairable"))\n',
             '''    console.log("LEARN_EXTENSION " + JSON.stringify({ phase: "tool_hook_then_schema", executed }))
'''),
            ("test/mcp.test.ts", "forwards the invoking session through direct and Code Mode MCP tools",
             '    expect(invocations[1]).toEqual({\n',
             '''    console.log("LEARN_EXTENSION " + JSON.stringify({
      phase: "mcp_paths", invocations,
      directNames: toolSet.definitions.map((tool) => tool.name),
      codeModeLookupPath: codeModeListings(toolSet.codeModeCatalog!).find((tool) => tool.path === "demo.search")?.path,
    }))
''')
        ],
    }
    checkout, bun, env = verified_runtime(path)
    rows = []
    for source, pattern, anchor, addition in data[slug]:
        original = subprocess.check_output(
            ["git", "-C", str(checkout), "show", f"{COMMIT}:packages/core/{source}"], text=True
        )
        instrumented = insert_in_case(original, pattern, anchor, addition)
        temporary = None
        try:
            with NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".test.ts", prefix="learn-extension-",
                                    dir=checkout / "packages/core" / Path(source).parent, delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(instrumented)
            _, output = report(["run", "test", str(temporary.relative_to(checkout / "packages/core")), "--test-name-pattern", pattern],
                               checkout, bun, env)
            matches = [json.loads(line[len(PREFIX):]) for line in output.splitlines() if line.startswith(PREFIX)]
            if len(matches) != 1:
                raise RuntimeError(f"预期一条原版观测，实际为 {len(matches)} 条")
            rows.extend(matches)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
    return rows

def cli_help(path):
    output = execute(path, "cli", ["run", "src/index.ts", "--help"], tests=False)
    if "SUBCOMMANDS" not in output or not re.search(r"(?m)^\s+run\s+", output):
        raise RuntimeError(output[-2000:])
    return output

def protocol_generated(path):
    execute(path, "protocol", ["run", "check:generated"], tests=False)
    return "bun run check:generated · OpenAPI 生成物一致性通过"

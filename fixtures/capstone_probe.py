"""Run both classroom scenarios in the original pinned Core test harness."""

import json
from pathlib import Path
import subprocess
from tempfile import NamedTemporaryFile

from storage_probe import COMMIT, report, verified_runtime

PREFIX = "LEARN_CAPSTONE "

def run_capstone(path):
    checkout, bun, env = verified_runtime(path)
    test = "packages/core/test/subagent-idle-e2e.test.ts"
    original = subprocess.check_output(
        ["git", "-C", str(checkout), "show", f"{COMMIT}:{test}"], text=True
    )
    scenario = Path(__file__).with_name("capstone-scenario.ts").read_text()
    temporary = None
    try:
        with NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".test.ts", prefix="learn-capstone-",
                                dir=checkout / "packages/core/test", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(original + "\n" + scenario)
        counts, output = report(["run", "test", f"test/{temporary.name}", "--test-name-pattern", "classroom full chain"],
                                checkout, bun, env)
        rows = [json.loads(line[len(PREFIX):]) for line in output.splitlines() if line.startswith(PREFIX)]
        if counts != {"pass": 2, "fail": 0} or len(rows) != 10:
            raise RuntimeError(f"未完成两套综合实验：{counts}，{len(rows)} 条记录\n{output[-4000:]}")
        return {"commit": COMMIT, "counts": counts, "observations": rows}
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)

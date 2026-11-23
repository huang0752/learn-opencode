// Classroom scenarios appended to a temporary copy of the upstream subagent-idle-e2e test.
// Uses its original boot, file SQLite, tool registry, SessionRunner, Job and TestLLM harness.
describe("Learn OpenCode capstone", () => {
  for (const fixture of [
    {
      name: "procurement",
      objective: "核查 ISO 9001 商务要求，缺证据时待复核。",
      material: "投标人华宁设备服务有限公司。投标截止日 2026-11-25。\n",
      childTask: "定位证书原文，回报页码和有效期。",
      evidence: "P12｜证书持有人华宁设备服务有限公司，有效期至 2027-06-30。",
      decision: "符合",
    },
    {
      name: "release-review",
      objective: "核查发布回归证明，缺退出码时待复核。",
      material: "发布验收需要用例编号和命令退出码。\n",
      childTask: "检查回归日志中是否有最终退出码。",
      evidence: "LOG-42｜找到回归日志，缺少最终退出码。",
      decision: "待复核",
    },
  ]) {
    e2e.live(
      "classroom full chain " + fixture.name,
      () => Effect.gen(function* () {
        const marker = "LEARN_CAPSTONE "
        const record = (phase: string, fields: Record<string, unknown>) =>
          console.log(marker + JSON.stringify({ scenario: fixture.name, phase, ...fields }))
        const base = yield* setup()
        const dbPath = path.join(base.dir.path, "capstone.sqlite")
        const firstScope = yield* Scope.make()
        yield* Effect.addFinalizer(() => Scope.close(firstScope, Exit.void))
        const first = yield* boot(firstScope, {
          database: dbPath, global: base.global, llm: base.llmContext,
        })
        yield* prepareLocation(first, base.location)
        const registry = yield* Tool.Service.pipe(Effect.provide(first.locations.get(base.location)))
        const parent = yield* first.sessions.create({
          location: base.location,
          title: "课堂综合核查",
          model: Model.Ref.make({ id: Model.ID.make("parent"), providerID: Provider.ID.make("test") }),
        })

        // Seed a substantial earlier transcript, then use the original tool to dispatch a child.
        yield* base.llm.always(TestLLM.text("已接收材料，等待取证。", "classroom-receipt"))
        yield* first.sessions.prompt({ sessionID: parent.id, text: fixture.objective + "\n" + fixture.material.repeat(130) })
        yield* first.sessions.wait(parent.id)
        yield* base.llm.serve(script({
          reviewer: [
            TestLLM.text("这条预设响应随旧服务作用域中断。", "before-restart"),
            TestLLM.text(fixture.evidence, "after-restart"),
          ],
          build: [TestLLM.text("已收到后台证据。", "received-report")],
        }))
        const gate = yield* base.llm.gate()
        const launched = yield* executeTool(registry, {
          sessionID: parent.id,
          ...toolIdentity,
          call: {
            type: "tool-call", id: "classroom-dispatch", name: SubagentTool.name,
            input: { agent: "reviewer", description: fixture.name, prompt: fixture.childTask },
          },
        })
        const childID = outputSessionID(launched.metadata)
        yield* gate.started
        expect((yield* claims(first))[childID]).toBe(true)
        const jobsBefore = yield* first.jobs.pendingBackground
        expect(jobsBefore).toMatchObject([{ id: childID, status: "running" }])
        record("before_close", {
          childClaim: (yield* claims(first))[childID],
          jobStatuses: jobsBefore.map((job) => job.status),
          parentReports: (yield* deliveredReports(first, parent.id)).length,
        })
        yield* Scope.close(firstScope, Exit.void)
        yield* gate.release

        const secondScope = yield* Scope.make()
        yield* Effect.addFinalizer(() => Scope.close(secondScope, Exit.void))
        const second = yield* boot(secondScope, {
          database: dbPath, global: base.global, llm: base.llmContext,
        })
        yield* prepareLocation(second, base.location)
        expect((yield* claims(second))[childID]).toBe(true)
        record("reopened", {
          childClaim: (yield* claims(second))[childID],
          jobStatuses: (yield* second.jobs.pendingBackground).map((job) => job.status),
        })
        yield* second.restart.resumeSuspendedSessions
        yield* waitForReports(second, parent.id, 1)
        const reports = yield* deliveredReports(second, parent.id)
        expect(reports).toHaveLength(1)
        expect(reports[0]?.text).toContain(fixture.evidence)
        expect((yield* claims(second))[childID]).toBe(false)
        yield* second.restart.resumeSuspendedSessions
        const replayedReports = yield* deliveredReports(second, parent.id)
        expect(replayedReports).toHaveLength(1)
        const childCalls = (yield* base.llm.requests()).filter((r) => r.model.id === "reviewer").length
        expect(childCalls).toBe(2)
        record("report_delivered", { childCalls, report: reports[0]?.text, replayCount: replayedReports.length })

        const beforeSummary = (yield* base.llm.requests()).length
        const summary = "## Objective\n- " + fixture.objective + "\n## Important Context\n- " + fixture.evidence
        yield* base.llm.always(TestLLM.text(summary, "classroom-summary"))
        const admitted = yield* second.sessions.compact({ sessionID: parent.id })
        yield* second.sessions.wait(parent.id)
        const compacted = (yield* second.sessions.messages({ sessionID: parent.id }))
          .find((message) => message.id === admitted.id)
        expect(compacted).toMatchObject({ type: "compaction", status: "completed", summary })
        const summaryRequest = (yield* base.llm.requests())[beforeSummary]
        expect(JSON.stringify(summaryRequest?.messages)).toContain(fixture.evidence)
        record("compaction_completed", {
          checkpoint: compacted?.id,
          summary,
          evidenceWasInSummaryRequest: JSON.stringify(summaryRequest?.messages).includes(fixture.evidence),
        })

        const beforeFinal = (yield* base.llm.requests()).length
        const followup = "按已取得的材料给出最终核查结论，并列出证据定位。"
        const conclusion = fixture.decision + "｜" + fixture.evidence
        yield* base.llm.always(TestLLM.text(conclusion, "classroom-final"))
        yield* second.sessions.prompt({ sessionID: parent.id, text: followup })
        yield* second.sessions.wait(parent.id)
        const finalRequest = (yield* base.llm.requests())[beforeFinal]
        const contents = JSON.stringify(finalRequest?.messages)
        expect(contents).toContain("<summary>")
        expect(contents).toContain(fixture.evidence)
        expect(contents).toContain(followup)
        expect(yield* second.sessions.context(parent.id)).toContainEqual(
          expect.objectContaining({ type: "assistant", content: expect.arrayContaining([
            expect.objectContaining({ text: conclusion }),
          ]) }),
        )
        expect((yield* base.llm.requests()).filter((r) => r.model.id === "reviewer")).toHaveLength(2)
        record("final_request", {
          conclusion,
          roles: finalRequest?.messages.map((message) => message.role),
          evidenceInRequest: contents.includes(fixture.evidence),
          summaryInRequest: contents.includes("<summary>"),
          originalChildCalls: childCalls,
        })
      }),
      30_000,
    )
  }
})

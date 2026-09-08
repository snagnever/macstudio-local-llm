import { describe, expect, test } from "bun:test"
import {
  activeDuration,
  collectSubagentDetails,
  collectSubagentStats,
  estimateDeltaTokens,
  formatRate,
  formatTokens,
  liveTokensPerSecond,
  subagentSessionID,
} from "../lib/subagent-sidebar-core"

describe("subagent sidebar", () => {
  test("selects only child session routes", () => {
    expect(subagentSessionID({ name: "home" }, "ses_parent")).toBeUndefined()
    expect(subagentSessionID({ name: "session", params: { sessionID: "ses_main" } })).toBeUndefined()
    expect(subagentSessionID({ name: "session", params: { sessionID: "ses_child" } }, "ses_main")).toBe(
      "ses_child",
    )
  })

  test("formats compact token counts and rates", () => {
    expect(formatTokens(999)).toBe("999")
    expect(formatTokens(1_250)).toBe("1.3k")
    expect(formatTokens(1_250_000)).toBe("1.3M")
    expect(formatRate(8.126)).toBe("8.13")
    expect(formatRate(42.14)).toBe("42.1")
    expect(formatRate(1_250)).toBe("1.3k")
  })

  test("calculates estimated live throughput from recent stream deltas", () => {
    expect(estimateDeltaTokens("hello")).toBe(1)
    expect(estimateDeltaTokens("abcdefghij")).toBe(2)

    const samples = [
      { tokens: 10, timestamp: 1_000 },
      { tokens: 20, timestamp: 1_500 },
      { tokens: 30, timestamp: 2_000 },
    ]

    expect(activeDuration(samples, 2_250)).toBe(1_250)
    expect(liveTokensPerSecond(samples, 2_250, 5_000)).toBe(48)
    expect(liveTokensPerSecond(samples, 8_000, 5_000)).toBeUndefined()
  })

  test("aggregates tokens, decode time, cost and toolcalls", () => {
    const parts = new Map([
      [
        "msg_1",
        [
          { type: "reasoning", time: { start: 1_500, end: 2_000 } },
          { type: "tool", tool: "read", state: { status: "completed", time: { start: 2_000, end: 2_100 } } },
        ],
      ],
      [
        "msg_2",
        [
          { type: "text", time: { start: 4_500, end: 5_000 } },
          { type: "tool", tool: "bash", state: { status: "error", time: { start: 5_000, end: 5_100 } } },
          { type: "tool", tool: "grep", state: { status: "running", time: { start: 5_200 } } },
        ],
      ],
    ])

    const result = collectSubagentStats(
      [
        {
          id: "msg_1",
          role: "assistant",
          providerID: "local",
          modelID: "model-a",
          cost: 0.01,
          time: { created: 1_000, completed: 3_000 },
          tokens: { input: 500, output: 100, reasoning: 20, cache: { read: 200, write: 10 } },
        },
        { id: "msg_user", role: "user", time: { created: 3_500 } },
        {
          id: "msg_2",
          role: "assistant",
          providerID: "local",
          modelID: "model-b",
          cost: 0.02,
          time: { created: 4_000, completed: 5_500 },
          tokens: { input: 600, output: 50, reasoning: 10, cache: { read: 300, write: 20 } },
        },
      ],
      (messageID) => parts.get(messageID) ?? [],
    )

    expect(result).toEqual({
      context: 980,
      input: 1_100,
      output: 150,
      reasoning: 30,
      cacheRead: 500,
      cacheWrite: 30,
      cost: 0.03,
      decodeMs: 2_500,
      tokensPerSecond: 60,
      prefillMs: 500,
      promptTokensPerSecond: 1_200,
      toolcalls: 3,
      failedTools: 1,
      runningTool: "grep",
      providerID: "local",
      modelID: "model-b",
    })
  })

  test("derives output slices, tool counts and recent files", () => {
    const parts = new Map([
      [
        "msg_output",
        [
          { id: "think", type: "reasoning", text: "abcdefghij", time: { start: 1_000, end: 1_400 } },
          { id: "answer", type: "text", text: "abcdefghij", time: { start: 1_400, end: 1_600 } },
          {
            id: "shell",
            type: "tool",
            tool: "bash",
            state: { status: "completed", input: { command: "abcdefghij" } },
          },
        ],
      ],
      [
        "msg_tools",
        [
          {
            id: "read",
            type: "tool",
            tool: "read",
            state: { status: "completed", input: { filePath: "/project/a.ts" } },
          },
          {
            id: "edit",
            type: "tool",
            tool: "edit",
            state: { status: "error", input: { filePath: "/project/b.ts" } },
          },
          {
            id: "skill",
            type: "tool",
            tool: "skill",
            state: { status: "running", input: { name: "testing" }, time: { start: 2_000 } },
          },
        ],
      ],
    ])

    const result = collectSubagentDetails(
      [
        {
          id: "msg_output",
          role: "assistant",
          tokens: { input: 20, output: 90, cache: { read: 80 } },
        },
        {
          id: "msg_tools",
          role: "assistant",
          tokens: { input: 0, output: 0, cache: { read: 0 } },
        },
      ],
      (messageID) => parts.get(messageID) ?? [],
    )

    expect(result.output).toEqual({
      total: 90,
      thinking: 30,
      message: 30,
      tool: 30,
      toolFile: 0,
      toolShell: 30,
      toolOther: 0,
      thinkingPercent: 33,
      messagePercent: 33,
      toolPercent: 33,
      thinkingTimePercent: 67,
      messageTimePercent: 33,
      cacheRead: 80,
      cacheHitPercent: 80,
    })
    expect(result.tools).toEqual({
      total: 4,
      failed: 1,
      running: { tool: "skill", start: 2_000 },
      skill: "testing",
      read: ["/project/a.ts"],
      edited: ["/project/b.ts"],
      rows: [
        ["bash", 1],
        ["read", 1],
        ["edit", 1],
        ["skill", 1],
      ],
    })
  })
})

/** @jsxImportSource @opentui/solid */
import { For, Show, createMemo, createSignal } from "solid-js"
import type { TuiPlugin } from "@opencode-ai/plugin/tui"
import {
  collectSubagentDetails,
  collectSubagentStats,
  estimateDeltaTokens,
  formatRate,
  formatTokens,
  liveTokensPerSecond,
  subagentSessionID,
  type ThroughputSample,
} from "../lib/subagent-sidebar-core"

interface PartDeltaEvent {
  type: "message.part.delta"
  properties: {
    sessionID: string
    messageID: string
    partID: string
    field: string
    delta: string
  }
}

interface LiveResponse {
  messageID: string
  created: number
  firstDeltaAt?: number
}

const WINDOW_MS = 5_000
const TICK_MS = 500
const WARN_PERCENT = 75
const DANGER_PERCENT = 90
const LABEL_WIDTH = 11
const MAX_TOOL_ROWS = 6
const MAX_PATH_CHARS = 38

const money = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  minimumFractionDigits: 4,
})

function formatSeconds(milliseconds: number) {
  const seconds = milliseconds / 1_000
  return seconds < 10 ? `${seconds.toFixed(1)}s` : `${Math.round(seconds)}s`
}

function bar(percent: number, width = 18) {
  const filled = Math.max(0, Math.min(width, Math.round((percent / 100) * width)))
  return "█".repeat(filled) + "░".repeat(width - filled)
}

function row(label: string, value: string) {
  return `  ${label.padEnd(LABEL_WIDTH)}${value}`
}

const tui: TuiPlugin = async (api) => {
  const samples = new Map<string, ThroughputSample[]>()
  const streamTokens = new Map<string, number>()
  const live = new Map<string, LiveResponse>()
  const [shown, setShown] = createSignal(true)
  const [version, setVersion] = createSignal(0)
  const [tick, setTick] = createSignal(0)
  const bump = () => setVersion((value) => value + 1)

  const unsubDelta = api.event.on(
    "message.part.delta" as unknown as "message.part.delta",
    (event: PartDeltaEvent) => {
      if (event.properties.field !== "text" || !event.properties.delta) return
      const sessionID = event.properties.sessionID
      const now = Date.now()
      const pending = live.get(sessionID)
      if (pending && pending.firstDeltaAt === undefined) pending.firstDeltaAt = now

      const tokens = estimateDeltaTokens(event.properties.delta)
      const list = samples.get(sessionID) ?? []
      list.push({ tokens, timestamp: now })
      samples.set(sessionID, list)
      streamTokens.set(sessionID, (streamTokens.get(sessionID) ?? 0) + tokens)
      bump()
    },
  )

  const unsubUpdated = api.event.on("message.updated", (event) => {
    const info = event.properties.info as any
    if (info.role !== "assistant") return
    if (info.time.completed) {
      samples.delete(info.sessionID)
      streamTokens.delete(info.sessionID)
      live.delete(info.sessionID)
      bump()
      return
    }

    const current = live.get(info.sessionID)
    if (!current || current.messageID !== info.id) {
      live.set(info.sessionID, { messageID: info.id, created: info.time.created })
      samples.delete(info.sessionID)
      streamTokens.delete(info.sessionID)
      bump()
    }
  })

  const unsubPart = api.event.on("message.part.updated", (event) => {
    const part = event.properties.part as any
    if (part.type !== "tool") return
    samples.delete(part.sessionID)
    bump()
  })

  const unsubError = api.event.on("session.error", () => {
    samples.clear()
    streamTokens.clear()
    live.clear()
    bump()
  })

  const interval = setInterval(() => {
    const cutoff = Date.now() - WINDOW_MS
    for (const [sessionID, list] of samples) {
      const recent = list.filter((sample) => sample.timestamp >= cutoff)
      if (recent.length !== list.length) samples.set(sessionID, recent)
    }
    setTick((value) => value + 1)
  }, TICK_MS)

  api.lifecycle.onDispose(() => {
    unsubDelta()
    unsubUpdated()
    unsubPart()
    unsubError()
    clearInterval(interval)
  })

  api.keymap.registerLayer({
    commands: [
      {
        name: "subagent.sidebar.toggle",
        title: "Toggle subagent sidebar",
        category: "Subagents",
        namespace: "palette",
        slashName: "subagent-sidebar",
        run() {
          setShown((value) => !value)
        },
      },
    ],
  })

  function shortPath(path: string) {
    const root = api.state.path.worktree
    if (root && path.startsWith(root + "/")) return path.slice(root.length + 1)
    return path
  }

  function truncatePath(path: string) {
    if (path.length <= MAX_PATH_CHARS) return path
    return "…" + path.slice(path.length - MAX_PATH_CHARS + 1)
  }

  function referenceFile(path: string) {
    api.client.tui.appendPrompt({ text: ` @${shortPath(path)}` }).catch(() => {})
  }

  api.slots.register({
    order: 400,
    slots: {
      app(ctx) {
        const panel = createMemo(() => {
          version()
          tick()
          if (!shown()) return

          const route = api.route.current
          if (route.name !== "session") return
          const routeSessionID = route.params?.sessionID
          if (typeof routeSessionID !== "string") return
          const session = api.state.session.get(routeSessionID)
          const sessionID = subagentSessionID(route, session?.parentID)
          if (!sessionID) return

          const messages = api.state.session.messages(sessionID) as any[]
          const getParts = (messageID: string) => api.state.part(messageID) as any[]
          const stats = collectSubagentStats(messages, getParts)
          const details = collectSubagentDetails(messages, getParts)
          const current = messages.findLast((message) => message.role === "assistant")
          const providerID = stats.providerID ?? current?.providerID
          const modelID = stats.modelID ?? current?.modelID
          const provider = api.state.provider.find((item) => item.id === providerID)
          const model = modelID ? provider?.models[modelID] : undefined
          const limit = model?.limit.context ?? 0
          const status = api.state.session.status(sessionID)?.type ?? "idle"
          const pending = status === "idle" ? undefined : live.get(sessionID)
          const phase = pending
            ? pending.firstDeltaAt === undefined
              ? ("prefill" as const)
              : ("decode" as const)
            : ("idle" as const)
          const estimatedOutput = streamTokens.get(sessionID) ?? 0
          const context = stats.context + estimatedOutput
          const contextPercent = limit > 0 ? Math.round((context / limit) * 100) : undefined
          const now = Date.now()
          const liveTps = liveTokensPerSecond(samples.get(sessionID) ?? [], now, WINDOW_MS)
          const prefillMs = pending
            ? (pending.firstDeltaAt ?? now) - pending.created
            : stats.prefillMs

          return {
            title: session?.title ?? "Subagent",
            agent: session?.agent,
            status,
            phase,
            model: model?.name ?? modelID,
            context,
            contextPercent,
            contextLimit: limit,
            contextEstimated: estimatedOutput > 0,
            estimatedOutput,
            input: stats.input,
            output: stats.output,
            reasoning: stats.reasoning,
            cacheRead: stats.cacheRead,
            cacheWrite: stats.cacheWrite,
            cost: session?.cost ?? stats.cost,
            tokensPerSecond: phase === "decode" ? liveTps : stats.tokensPerSecond,
            tokensPerSecondEstimated: phase === "decode",
            prefillMs,
            promptTokensPerSecond: phase === "idle" ? stats.promptTokensPerSecond : undefined,
            liveElapsedMs: pending ? now - pending.created : undefined,
            details,
          }
        })

        const theme = () => ctx.theme.current
        const contextColor = (percent?: number) => {
          if (percent === undefined) return theme().textMuted
          if (percent >= DANGER_PERCENT) return theme().error
          if (percent >= WARN_PERCENT) return theme().warning
          return theme().success
        }

        return (
          <Show when={panel()}>
            {(item) => (
              <box
                position="absolute"
                top={0}
                right={0}
                bottom={0}
                width={46}
                paddingTop={1}
                paddingBottom={1}
                paddingLeft={2}
                paddingRight={2}
                backgroundColor={theme().backgroundPanel}
                border={["left"]}
                borderColor={theme().border}
              >
                <scrollbox
                  flexGrow={1}
                  verticalScrollbarOptions={{
                    trackOptions: {
                      backgroundColor: theme().background,
                      foregroundColor: theme().borderActive,
                    },
                  }}
                >
                  <box flexShrink={0} paddingRight={1}>
                <text fg={theme().text} wrapMode="word"><b>{item().title}</b></text>
                <Show when={item().agent}><text fg={theme().textMuted}>Agent: {item().agent}</text></Show>
                <Show when={item().model}><text fg={theme().textMuted}>Model: {item().model}</text></Show>
                <text fg={item().status === "idle" ? theme().success : theme().warning}>
                  Status: {item().status} · {item().phase}
                </text>

                <text marginTop={1} fg={theme().text}><b>Context</b></text>
                <Show when={item().contextPercent !== undefined}>
                  <text fg={contextColor(item().contextPercent)}>
                    {"  " + bar(item().contextPercent!)} {item().contextPercent}%
                  </text>
                </Show>
                <text fg={theme().textMuted}>
                  {row(
                    "tokens",
                    `${item().contextEstimated ? "~" : ""}${formatTokens(item().context)}` +
                      (item().contextLimit > 0 ? ` / ${formatTokens(item().contextLimit)}` : ""),
                  )}
                </text>
                <Show when={item().prefillMs !== undefined}>
                  <text fg={theme().textMuted}>
                    {row(
                      "prefill",
                      formatSeconds(item().prefillMs!) +
                        (item().promptTokensPerSecond
                          ? ` · pp ${formatRate(item().promptTokensPerSecond!)} t/s`
                          : item().phase === "prefill"
                            ? "…"
                            : ""),
                    )}
                  </text>
                </Show>
                <Show when={item().tokensPerSecond !== undefined && item().tokensPerSecond! > 0}>
                  <text fg={item().tokensPerSecondEstimated ? theme().warning : theme().textMuted}>
                    {row(
                      "decode",
                      `${item().tokensPerSecondEstimated ? "~" : ""}${formatRate(item().tokensPerSecond!)} tok/s`,
                    )}
                  </text>
                </Show>
                <Show when={item().liveElapsedMs !== undefined}>
                  <text fg={theme().textMuted}>{row("elapsed", formatSeconds(item().liveElapsedMs!))}</text>
                </Show>

                <text marginTop={1} fg={theme().text}><b>Usage</b></text>
                <text fg={theme().textMuted}>{row("input", formatTokens(item().input))}</text>
                <text fg={theme().textMuted}>
                  {row("output", formatTokens(item().output + item().estimatedOutput) + (item().estimatedOutput ? " ~" : ""))}
                </text>
                <text fg={theme().textMuted}>{row("reasoning", formatTokens(item().reasoning))}</text>
                <text fg={theme().textMuted}>{row("cache read", formatTokens(item().cacheRead))}</text>
                <text fg={theme().textMuted}>{row("cache write", formatTokens(item().cacheWrite))}</text>
                <text fg={theme().textMuted}>{row("cost", money.format(item().cost))}</text>

                <Show when={item().details.output?.total ? item().details.output : undefined} keyed>
                  {(output) => (
                      <>
                        <text marginTop={1} fg={theme().text}><b>Output</b></text>
                        <text fg={theme().textMuted}>  {formatTokens(output.total)} tok · split estimated</text>
                        <text fg={theme().textMuted}>
                          {row(
                            "think",
                            `${output.thinkingPercent ?? 0}% · ${formatTokens(output.thinking)}` +
                              (output.thinkingTimePercent !== undefined
                                ? ` · time ${output.thinkingTimePercent}%`
                                : ""),
                          )}
                        </text>
                        <text fg={theme().textMuted}>
                          {row(
                            "message",
                            `${output.messagePercent ?? 0}% · ${formatTokens(output.message)}` +
                              (output.messageTimePercent !== undefined
                                ? ` · time ${output.messageTimePercent}%`
                                : ""),
                          )}
                        </text>
                        <text fg={theme().textMuted}>
                          {row("tool", `${output.toolPercent ?? 0}% · ${formatTokens(output.tool)}`)}
                        </text>
                        <Show when={output.toolFile > 0}>
                          <text fg={theme().textMuted}>{row("  file", formatTokens(output.toolFile))}</text>
                        </Show>
                        <Show when={output.toolShell > 0}>
                          <text fg={theme().textMuted}>{row("  shell", formatTokens(output.toolShell))}</text>
                        </Show>
                        <Show when={output.toolOther > 0}>
                          <text fg={theme().textMuted}>{row("  other", formatTokens(output.toolOther))}</text>
                        </Show>
                        <Show when={output.cacheHitPercent !== undefined}>
                          <text fg={theme().textMuted}>
                            {row("cache", `${output.cacheHitPercent}% hit · ${formatTokens(output.cacheRead)} read`)}
                          </text>
                        </Show>
                      </>
                    )}
                </Show>

                <Show when={item().details.tools}>
                  {(tools) => (
                    <>
                      <text marginTop={1} fg={theme().text}><b>Tools</b></text>
                      <Show when={tools().running}>
                        <text fg={theme().warning}>
                          {row(
                            "running",
                            tools().running!.tool +
                              (tools().running!.start
                                ? ` · ${formatSeconds(Date.now() - tools().running!.start!)}`
                                : ""),
                          )}
                        </text>
                      </Show>
                      <text fg={theme().textMuted}>
                        {row("total", `${tools().total}${tools().failed ? ` · ${tools().failed} failed` : ""}`)}
                      </text>
                      <For each={tools().rows.slice(0, MAX_TOOL_ROWS)}>
                        {(entry) => <text fg={theme().textMuted}>{row(entry[0], String(entry[1]))}</text>}
                      </For>
                      <Show when={tools().rows.length > MAX_TOOL_ROWS}>
                        <text fg={theme().textMuted}>
                          {row("", `+${tools().rows.length - MAX_TOOL_ROWS} more`)}
                        </text>
                      </Show>

                      <Show when={tools().read.length > 0}>
                        <text marginTop={1} fg={theme().text}><b>Read</b></text>
                        <For each={tools().read}>
                          {(path) => (
                            <text fg={theme().textMuted} onMouseDown={() => referenceFile(path)}>
                              {"  " + truncatePath(shortPath(path))}
                            </text>
                          )}
                        </For>
                      </Show>
                      <Show when={tools().edited.length > 0}>
                        <text marginTop={1} fg={theme().text}><b>Edited</b></text>
                        <For each={tools().edited}>
                          {(path) => (
                            <text fg={theme().textMuted} onMouseDown={() => referenceFile(path)}>
                              {"  " + truncatePath(shortPath(path))}
                            </text>
                          )}
                        </For>
                      </Show>
                    </>
                  )}
                </Show>

                <text marginTop={1} fg={theme().text}><b>Session</b></text>
                <Show when={item().details.tools?.skill}>
                  <text fg={theme().textMuted}>{row("skill", item().details.tools!.skill!)}</text>
                </Show>
                <Show when={api.state.path.directory}>
                  <text fg={theme().textMuted}>{row("cwd", truncatePath(shortPath(api.state.path.directory)))}</text>
                </Show>
                <Show when={api.state.path.worktree !== api.state.path.directory}>
                  <text fg={theme().textMuted}>{row("project", truncatePath(shortPath(api.state.path.worktree)))}</text>
                </Show>
                  </box>
                </scrollbox>
              </box>
            )}
          </Show>
        )
      },
    },
  })
}

export default {
  id: "opencode-subagent-sidebar",
  tui,
}

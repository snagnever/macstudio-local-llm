export interface RouteState {
  name: string
  params?: Record<string, unknown>
}

export interface UsageMessage {
  id: string
  role: string
  providerID?: string
  modelID?: string
  cost?: number
  time?: { created?: number; completed?: number }
  tokens?: {
    input?: number
    output?: number
    reasoning?: number
    cache?: { read?: number; write?: number }
  }
}

export interface UsagePart {
  id?: string
  type: string
  text?: string
  tool?: string
  time?: { start?: number; end?: number; created?: number }
  state?: {
    status?: string
    time?: { start?: number; end?: number }
    input?: Record<string, unknown>
  }
}

export interface ThroughputSample {
  tokens: number
  timestamp: number
}

const BYTES_PER_TOKEN = 5
const TAIL_CAP_MS = 1_000
const MIN_DURATION_MS = 250

export function estimateDeltaTokens(delta: string) {
  if (!delta) return 0
  return Math.max(1, Math.ceil(new TextEncoder().encode(delta).length / BYTES_PER_TOKEN))
}

export function activeDuration(samples: readonly ThroughputSample[], now: number) {
  if (samples.length === 0) return 0
  if (samples.length === 1) {
    return Math.min(Math.max(now - samples[0].timestamp, MIN_DURATION_MS), TAIL_CAP_MS)
  }

  let total = 0
  for (let index = 1; index < samples.length; index++) {
    total += Math.max(0, samples[index].timestamp - samples[index - 1].timestamp)
  }
  total += Math.min(Math.max(0, now - samples[samples.length - 1].timestamp), TAIL_CAP_MS)
  return Math.max(total, MIN_DURATION_MS)
}

export function liveTokensPerSecond(
  samples: readonly ThroughputSample[],
  now: number,
  windowMs: number,
) {
  const recent = samples.filter((sample) => sample.timestamp >= now - windowMs)
  if (recent.length === 0) return
  const tokens = recent.reduce((total, sample) => total + sample.tokens, 0)
  const duration = activeDuration(recent, now)
  return duration > 0 ? (tokens / duration) * 1_000 : undefined
}

export function collectSubagentDetails(
  messages: readonly UsageMessage[],
  parts: (messageID: string) => readonly UsagePart[],
) {
  const toolCounts = new Map<string, number>()
  const read: string[] = []
  const edited: string[] = []
  let toolTotal = 0
  let failed = 0
  let running: { tool: string; start?: number } | undefined
  let skill: string | undefined
  let cacheRead = 0
  let freshInput = 0
  let outputTotal = 0
  let thinking = 0
  let answer = 0
  let toolFile = 0
  let toolShell = 0
  let toolOther = 0
  let thinkingMs = 0
  let answerMs = 0

  for (const message of messages) {
    if (message.role !== "assistant") continue
    const tokens = message.tokens
    const messageParts = parts(message.id)
    cacheRead += tokens?.cache?.read ?? 0
    freshInput += tokens?.input ?? 0

    for (const part of messageParts) {
      if (part.type !== "tool") continue
      const name = part.tool ?? "unknown"
      const input = part.state?.input
      toolCounts.set(name, (toolCounts.get(name) ?? 0) + 1)
      toolTotal++
      if (part.state?.status === "error") failed++
      if (part.state?.status === "running" || part.state?.status === "pending") {
        running = { tool: name, start: part.state?.time?.start }
      }
      if (name === "skill" && typeof input?.name === "string") skill = input.name
      if (name === "read" && typeof input?.filePath === "string") read.push(input.filePath)
      if (
        (name === "write" || name === "edit" || name === "patch" || name === "multiedit") &&
        typeof input?.filePath === "string"
      ) {
        edited.push(input.filePath)
      }
    }

    const generated = tokens?.output ?? 0
    if (generated <= 0) continue
    outputTotal += generated
    let thinkingSize = 0
    let answerSize = 0
    let fileSize = 0
    let shellSize = 0
    let otherSize = 0

    for (const part of messageParts) {
      if (part.type === "reasoning") {
        thinkingSize += part.text?.length ?? 0
        if (part.time?.start !== undefined && part.time.end !== undefined) {
          thinkingMs += part.time.end - part.time.start
        }
        continue
      }
      if (part.type === "text") {
        answerSize += part.text?.length ?? 0
        if (part.time?.start !== undefined && part.time.end !== undefined) {
          answerMs += part.time.end - part.time.start
        }
        continue
      }
      if (part.type !== "tool") continue
      for (const [field, value] of Object.entries(part.state?.input ?? {})) {
        const size = typeof value === "string" ? value.length : JSON.stringify(value)?.length ?? 0
        if (part.tool === "bash") shellSize += size
        else if (FILE_FIELDS.has(field)) fileSize += size
        else otherSize += size
      }
    }

    const sizeTotal = thinkingSize + answerSize + fileSize + shellSize + otherSize
    if (sizeTotal <= 0) continue
    thinking += (thinkingSize / sizeTotal) * generated
    answer += (answerSize / sizeTotal) * generated
    toolFile += (fileSize / sizeTotal) * generated
    toolShell += (shellSize / sizeTotal) * generated
    toolOther += (otherSize / sizeTotal) * generated
  }

  const tool = toolFile + toolShell + toolOther
  const timeTotal = thinkingMs + answerMs
  const promptTokens = freshInput + cacheRead
  const percent = (part: number, whole: number) => (whole > 0 ? Math.round((part / whole) * 100) : undefined)

  return {
    output:
      outputTotal > 0 || promptTokens > 0
        ? {
            total: outputTotal,
            thinking: Math.round(thinking),
            message: Math.round(answer),
            tool: Math.round(tool),
            toolFile: Math.round(toolFile),
            toolShell: Math.round(toolShell),
            toolOther: Math.round(toolOther),
            thinkingPercent: percent(thinking, outputTotal),
            messagePercent: percent(answer, outputTotal),
            toolPercent: percent(tool, outputTotal),
            thinkingTimePercent: percent(thinkingMs, timeTotal),
            messageTimePercent: percent(answerMs, timeTotal),
            cacheRead,
            cacheHitPercent: percent(cacheRead, promptTokens),
          }
        : undefined,
    tools:
      toolTotal > 0
        ? {
            total: toolTotal,
            failed,
            running,
            skill,
            read: recent(read),
            edited: recent(edited),
            rows: [...toolCounts.entries()].sort((left, right) => right[1] - left[1]),
          }
        : undefined,
  }
}

const FILE_FIELDS = new Set(["content", "fileContent", "newString", "oldString", "newContent", "patch"])

function recent(paths: string[]) {
  const result: string[] = []
  const seen = new Set<string>()
  for (let index = paths.length - 1; index >= 0 && result.length < 3; index--) {
    if (seen.has(paths[index])) continue
    seen.add(paths[index])
    result.push(paths[index])
  }
  return result
}

export function formatTokens(value: number) {
  if (value < 1_000) return String(Math.round(value))
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`
  return `${(value / 1_000).toFixed(1)}k`
}

export function formatRate(value: number) {
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}k`
  if (value < 10) return value.toFixed(2)
  if (value < 100) return value.toFixed(1)
  return String(Math.round(value))
}

export function subagentSessionID(route: RouteState, parentID?: string) {
  if (route.name !== "session") return
  if (!parentID) return
  const sessionID = route.params?.sessionID
  if (typeof sessionID !== "string") return
  return sessionID
}

export function collectSubagentStats(
  messages: readonly UsageMessage[],
  parts: (messageID: string) => readonly UsagePart[],
) {
  const assistant = messages.filter((message) => message.role === "assistant")
  const last = assistant.findLast((message) => (message.tokens?.output ?? 0) > 0)
  const totals = assistant.reduce(
    (result, message) => {
      const tokens = message.tokens
      const messageParts = parts(message.id)
      const completed = message.time?.completed
      const start = messageParts.find(
        (part) => (part.type === "text" || part.type === "reasoning") && part.time?.start !== undefined,
      )?.time?.start
      const decodeMs = completed !== undefined && start !== undefined ? Math.max(0, completed - start) : 0

      result.input += tokens?.input ?? 0
      result.output += tokens?.output ?? 0
      result.reasoning += tokens?.reasoning ?? 0
      result.cacheRead += tokens?.cache?.read ?? 0
      result.cacheWrite += tokens?.cache?.write ?? 0
      result.cost += message.cost ?? 0
      result.decodeMs += decodeMs
      result.completedOutput += decodeMs > 0 ? (tokens?.output ?? 0) : 0

      for (const part of messageParts) {
        if (part.type !== "tool") continue
        result.toolcalls++
        if (part.state?.status === "error") result.failedTools++
        if (part.state?.status === "running" || part.state?.status === "pending") {
          result.runningTool = part.tool
        }
      }
      return result
    },
    {
      input: 0,
      output: 0,
      reasoning: 0,
      cacheRead: 0,
      cacheWrite: 0,
      cost: 0,
      decodeMs: 0,
      completedOutput: 0,
      toolcalls: 0,
      failedTools: 0,
      runningTool: undefined as string | undefined,
    },
  )
  const context = last?.tokens
  const lastStart = last
    ? parts(last.id).find(
        (part) => (part.type === "text" || part.type === "reasoning") && part.time?.start !== undefined,
      )?.time?.start
    : undefined
  const prefillMs =
    lastStart !== undefined && last?.time?.created !== undefined
      ? Math.max(0, lastStart - last.time.created)
      : undefined
  const lastInput = last?.tokens?.input ?? 0

  return {
    context: context
      ? (context.input ?? 0) +
        (context.output ?? 0) +
        (context.reasoning ?? 0) +
        (context.cache?.read ?? 0) +
        (context.cache?.write ?? 0)
      : 0,
    input: totals.input,
    output: totals.output,
    reasoning: totals.reasoning,
    cacheRead: totals.cacheRead,
    cacheWrite: totals.cacheWrite,
    cost: totals.cost,
    decodeMs: totals.decodeMs,
    tokensPerSecond: totals.decodeMs > 0 ? totals.completedOutput / (totals.decodeMs / 1000) : 0,
    prefillMs,
    promptTokensPerSecond:
      prefillMs !== undefined && prefillMs > 0 && lastInput > 0 ? lastInput / (prefillMs / 1000) : undefined,
    toolcalls: totals.toolcalls,
    failedTools: totals.failedTools,
    runningTool: totals.runningTool,
    providerID: last?.providerID,
    modelID: last?.modelID,
  }
}

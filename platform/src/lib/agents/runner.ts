/**
 * Generalized Agent Runner
 *
 * Core execution engine for the agent constellation. Each specialized agent
 * (Proposal, Build, Comms, Quality) uses this runner to invoke Claude via
 * the Agent SDK with isolated context and custom MCP tools.
 *
 * Pattern: Trigger.dev task -> runner.executeAgent() -> Agent SDK (Claude)
 *          -> DB state tracking -> waitpoint approval -> resume
 */

import {
  query,
  tool,
  createSdkMcpServer,
  type SDKAssistantMessage,
  type SDKResultMessage,
} from "@anthropic-ai/claude-agent-sdk"
import { z } from "zod"
import { db } from "@/lib/db"
import { agentTasks, agentLogs } from "@/lib/schema"
import { eq } from "drizzle-orm"

// ── Types ────────────────────────────────────────────────────────────────────

export type AgentType = "proposal" | "build" | "comms" | "quality" | "router"

export interface AgentRunOptions {
  /** The prompt for this agent invocation */
  prompt: string
  /** Working directory for file operations */
  cwd: string
  /** Agent-specific system prompt (defines role, context, constraints) */
  systemPrompt: string
  /** Maximum turns before the agent stops */
  maxTurns?: number
  /** Which built-in tools the agent can use */
  allowedTools?: string[]
  /** Additional MCP servers for this agent (e.g., Make.com, n8n) */
  mcpServers?: Record<string, ReturnType<typeof createSdkMcpServer>>
  /** Task ID for DB logging */
  taskId?: string
}

export interface AgentMessage {
  type: "text" | "tool_call" | "tool_result" | "error"
  content: string
}

export interface AgentResult {
  success: boolean
  result?: string
  error?: string
  messages: AgentMessage[]
  cost?: number
  turns?: number
}

// ── Built-in MCP tools (available to all agents) ────────────────────────────

// eslint-disable-next-line @typescript-eslint/no-unused-vars -- taskId reserved for per-task tool scoping
function createAgentTools(taskId?: string) {
  return createSdkMcpServer({
    name: "constellation",
    tools: [
      tool(
        "update_task_status",
        "Update the agent task status and current step in the database",
        {
          taskId: z.string().describe("Task UUID"),
          status: z
            .enum(["pending", "running", "waiting", "completed", "failed", "cancelled"])
            .describe("New task status"),
          currentStep: z.string().optional().describe("Current step name"),
        },
        async (args) => {
          await db
            .update(agentTasks)
            .set({
              status: args.status,
              ...(args.currentStep ? { currentStep: args.currentStep } : {}),
              updatedAt: new Date(),
              ...(args.status === "running" ? { startedAt: new Date() } : {}),
              ...(args.status === "completed" || args.status === "failed"
                ? { completedAt: new Date() }
                : {}),
            })
            .where(eq(agentTasks.id, args.taskId))
          return {
            content: [
              {
                type: "text" as const,
                text: `Task ${args.taskId} updated: status=${args.status}${args.currentStep ? ` step=${args.currentStep}` : ""}`,
              },
            ],
          }
        }
      ),
      tool(
        "log_event",
        "Log an event for tracking and debugging",
        {
          taskId: z.string().describe("Task UUID"),
          step: z.string().optional().describe("Step this log belongs to"),
          level: z.enum(["info", "warn", "error"]).describe("Log level"),
          message: z.string().describe("Log message"),
          metadata: z.string().optional().describe("JSON metadata string"),
        },
        async (args) => {
          await db.insert(agentLogs).values({
            taskId: args.taskId,
            step: args.step ?? null,
            level: args.level,
            message: args.message,
            metadata: args.metadata ?? null,
          })
          return {
            content: [
              { type: "text" as const, text: `Logged [${args.level}]: ${args.message}` },
            ],
          }
        }
      ),
    ],
  })
}

// ── Agent Execution ─────────────────────────────────────────────────────────

/**
 * Execute an agent with isolated context.
 *
 * Each agent gets its own Agent SDK session with:
 * - A specific system prompt (role, constraints, domain knowledge)
 * - Selected tools (not all tools — isolation by design)
 * - Optional MCP servers (e.g., Make.com for Build Agent)
 * - DB logging via constellation MCP tools
 */
export async function executeAgent(options: AgentRunOptions): Promise<AgentResult> {
  const messages: AgentMessage[] = []
  const constellationTools = createAgentTools(options.taskId)

  // Merge constellation tools with any agent-specific MCP servers
  const mcpServers: Record<string, ReturnType<typeof createSdkMcpServer>> = {
    constellation: constellationTools,
    ...(options.mcpServers ?? {}),
  }

  // Default tools: file access + constellation MCP
  const allowedTools = options.allowedTools ?? [
    "Read",
    "Glob",
    "Grep",
    "Write",
    "Edit",
    "Bash",
    "mcp__constellation__update_task_status",
    "mcp__constellation__log_event",
  ]

  try {
    for await (const message of query({
      prompt: options.prompt,
      options: {
        cwd: options.cwd,
        systemPrompt: options.systemPrompt,
        allowedTools,
        permissionMode: "bypassPermissions",
        allowDangerouslySkipPermissions: true,
        maxTurns: options.maxTurns ?? 50,
        mcpServers,
      },
    })) {
      if (message.type === "assistant") {
        const assistantMsg = message as SDKAssistantMessage
        if (assistantMsg.message?.content) {
          for (const block of assistantMsg.message.content) {
            if ("text" in block && typeof block.text === "string") {
              messages.push({ type: "text", content: block.text })
            }
            if ("type" in block && block.type === "tool_use" && "name" in block) {
              messages.push({ type: "tool_call", content: block.name as string })
            }
          }
        }
      }

      if (message.type === "result") {
        const resultMsg = message as SDKResultMessage
        if (resultMsg.subtype === "success") {
          return {
            success: true,
            result: resultMsg.result,
            messages,
            cost: resultMsg.total_cost_usd,
            turns: resultMsg.num_turns,
          }
        } else {
          return {
            success: false,
            error: "subtype" in resultMsg ? String(resultMsg.subtype) : "unknown",
            messages,
          }
        }
      }
    }
  } catch (err) {
    return {
      success: false,
      error: err instanceof Error ? err.message : String(err),
      messages,
    }
  }

  return {
    success: false,
    error: "Agent stream ended without result",
    messages,
  }
}

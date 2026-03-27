import { NextRequest, NextResponse } from "next/server";
import Anthropic from "@anthropic-ai/sdk";

const SYSTEM_PROMPT = `You are a support ticket classifier for a SaaS company. Analyze the ticket and return a JSON object with these fields:

- category: one of "billing", "technical", "feature_request", "account", "general"
- priority: one of "P1" (urgent, service down), "P2" (high, major feature broken), "P3" (medium, minor issue), "P4" (low, question or suggestion)
- escalation_tier: one of "tier_0" (auto-resolve, known issue with clear fix), "tier_1" (needs human review with AI-suggested response), "tier_2" (engineering escalation, likely a bug or infrastructure issue)
- confidence: float 0.0 to 1.0 indicating classification confidence
- suggested_response: a helpful 2-3 sentence response to the customer
- reasoning: brief explanation of why this classification was chosen

Return ONLY valid JSON, no markdown formatting.`;

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
};

export async function OPTIONS() {
  return new NextResponse(null, { status: 204, headers: corsHeaders });
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const ticket = body.ticket;

    if (!ticket || typeof ticket !== "string" || ticket.trim().length === 0) {
      return NextResponse.json(
        { error: "Missing or empty 'ticket' field in request body" },
        { status: 400, headers: corsHeaders }
      );
    }

    const apiKey = process.env.ANTHROPIC_API_KEY;
    if (!apiKey) {
      return NextResponse.json(
        { error: "AI service not configured" },
        { status: 503, headers: corsHeaders }
      );
    }

    const client = new Anthropic({ apiKey });

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 10_000);

    let message;
    try {
      message = await client.messages.create(
        {
          model: "claude-3-5-haiku-20241022",
          max_tokens: 512,
          system: SYSTEM_PROMPT,
          messages: [
            {
              role: "user",
              content: `Classify this support ticket:\n\n${ticket.trim()}`,
            },
          ],
        },
        { signal: controller.signal }
      );
    } finally {
      clearTimeout(timeout);
    }

    const textBlock = message.content.find((block) => block.type === "text");
    if (!textBlock || textBlock.type !== "text") {
      return NextResponse.json(
        { error: "No response from AI" },
        { status: 500, headers: corsHeaders }
      );
    }

    let text = textBlock.text.trim();
    // Claude sometimes wraps JSON in markdown code fences
    if (text.startsWith("```")) {
      text = text
        .replace(/^```(?:json)?\s*\n?/, "")
        .replace(/\n?```\s*$/, "");
    }

    const parsed = JSON.parse(text);

    return NextResponse.json(parsed, { headers: corsHeaders });
  } catch (err) {
    if (err instanceof Error && err.name === "AbortError") {
      return NextResponse.json(
        { error: "Classification timed out (10s limit)" },
        { status: 504, headers: corsHeaders }
      );
    }
    if (err instanceof SyntaxError) {
      return NextResponse.json(
        { error: "Failed to parse AI classification response" },
        { status: 500, headers: corsHeaders }
      );
    }
    const message = err instanceof Error ? err.message : "Unknown error";
    return NextResponse.json(
      { error: message },
      { status: 500, headers: corsHeaders }
    );
  }
}

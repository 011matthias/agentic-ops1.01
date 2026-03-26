import { NextRequest, NextResponse } from "next/server";
import Anthropic from "@anthropic-ai/sdk";

const VALID_CLIENT_TYPES = [
  "real-estate",
  "startup-founder",
  "consultant",
  "coach",
] as const;

type ClientType = (typeof VALID_CLIENT_TYPES)[number];

const SYSTEM_PROMPT = `You are a system architect specializing in AI-powered operator systems for busy professionals. Given a client type, generate a tailored system configuration.

Return ONLY valid JSON with this exact structure:
{
  "title": "System name for this client type",
  "dashboard_panels": [
    { "name": "Panel name", "description": "What this panel shows" }
  ],
  "agents": [
    { "name": "Agent name", "description": "What this agent does" }
  ],
  "integrations": ["Tool 1", "Tool 2"],
  "estimate": "Build time estimate"
}

Guidelines:
- Include 4-6 dashboard panels relevant to the client type
- Include 3-5 agents that solve real problems for this professional
- Include 4-8 integrations they would actually use
- Estimate should be "2-3 weeks" for standard builds
- Be specific to the industry, not generic
- Panel and agent names should be concrete, not abstract`;

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const clientType = body.client_type as ClientType;

    if (!clientType || !VALID_CLIENT_TYPES.includes(clientType)) {
      return NextResponse.json(
        {
          error: `Invalid client_type. Must be one of: ${VALID_CLIENT_TYPES.join(", ")}`,
        },
        { status: 400 }
      );
    }

    const apiKey = process.env.ANTHROPIC_API_KEY;
    if (!apiKey) {
      return NextResponse.json(
        { error: "AI service not configured" },
        { status: 503 }
      );
    }

    const client = new Anthropic({ apiKey });

    const clientTypeLabels: Record<ClientType, string> = {
      "real-estate": "Real Estate Agent",
      "startup-founder": "Startup Founder",
      consultant: "Business Consultant",
      coach: "Executive Coach",
    };

    const message = await client.messages.create({
      model: "claude-haiku-4-5-20251001",
      max_tokens: 1024,
      system: SYSTEM_PROMPT,
      messages: [
        {
          role: "user",
          content: `Generate a system configuration for a ${clientTypeLabels[clientType]}.`,
        },
      ],
    });

    const textBlock = message.content.find((block) => block.type === "text");
    if (!textBlock || textBlock.type !== "text") {
      return NextResponse.json(
        { error: "No response from AI" },
        { status: 500 }
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
    return NextResponse.json(parsed);
  } catch (err) {
    if (err instanceof SyntaxError) {
      return NextResponse.json(
        { error: "Failed to parse AI response" },
        { status: 500 }
      );
    }
    const message = err instanceof Error ? err.message : "Unknown error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}

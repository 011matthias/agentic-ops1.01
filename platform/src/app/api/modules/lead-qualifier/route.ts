import { NextRequest, NextResponse } from "next/server";
import Anthropic from "@anthropic-ai/sdk";

const SYSTEM_PROMPT = `You are a lead qualification AI for a Food & Beverage outreach system. Given a business description, analyze the lead and return a JSON object with these fields:

- score: integer 0-100 indicating how strong this lead is for F&B outreach
- reasoning: 2-3 sentences explaining the score (mention specific factors like cuisine type, location fit, online presence, growth signals)
- outreach_email: a personalized cold outreach email (3-4 paragraphs, conversational tone, mention something specific about their business, propose a concrete next step). The email should feel human-written, not templated.
- tags: array of 2-4 tags like "high-potential", "local", "new-business", "active-social", "catering", "franchise"

Scoring guidelines:
- 80-100: Strong lead (active business, clear contact path, growth signals)
- 60-79: Moderate lead (established but limited online presence or engagement)
- 40-59: Weak lead (minimal info, unclear fit, or saturated market)
- 0-39: Poor lead (closed, irrelevant category, or no contact path)

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
    const { business_name, business_type, location, website } = body;

    if (
      !business_name ||
      typeof business_name !== "string" ||
      business_name.trim().length === 0
    ) {
      return NextResponse.json(
        { error: "Missing or empty 'business_name' field" },
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

    const leadDescription = [
      `Business: ${business_name.trim()}`,
      business_type ? `Type: ${business_type.trim()}` : null,
      location ? `Location: ${location.trim()}` : null,
      website ? `Website: ${website.trim()}` : null,
    ]
      .filter(Boolean)
      .join("\n");

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 10_000);

    let message;
    try {
      message = await client.messages.create(
        {
          model: "claude-haiku-4-5-20251001",
          max_tokens: 1024,
          system: SYSTEM_PROMPT,
          messages: [
            {
              role: "user",
              content: `Qualify this lead for F&B outreach:\n\n${leadDescription}`,
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
        { error: "Lead qualification timed out (10s limit)" },
        { status: 504, headers: corsHeaders }
      );
    }
    if (err instanceof SyntaxError) {
      return NextResponse.json(
        { error: "Failed to parse AI response" },
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

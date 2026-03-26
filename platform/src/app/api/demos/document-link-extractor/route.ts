import { NextRequest, NextResponse } from "next/server";
import Anthropic from "@anthropic-ai/sdk";

const client = new Anthropic();

const SYSTEM_PROMPT = `You are a financial document link extractor. Given raw HTML from a company's investor relations page, extract and classify all document links.

For each link found, return:
- url: the full URL (resolve relative URLs if possible)
- title: the link text or document title
- type: one of "Annual Report", "Quarterly Filing", "Investor Presentation", "Press Release", "SEC Filing", "Earnings Call Transcript", "Proxy Statement", "Other"
- confidence: 0-100 score for classification confidence
- year: extracted year if identifiable, otherwise null

Also return rejected links (navigation, privacy policy, social media, etc.) in a separate array with a brief reason.

Return valid JSON only. No markdown, no explanation. Format:
{
  "company": "detected company name or null",
  "documents": [...],
  "rejected": [{"url": "...", "reason": "..."}],
  "summary": "brief one-line summary of what was found"
}`;

export async function POST(request: NextRequest) {
  try {
    const { html } = await request.json();

    if (!html || typeof html !== "string") {
      return NextResponse.json(
        { error: "Missing or invalid 'html' field. Provide HTML content as a string." },
        { status: 400 }
      );
    }

    if (html.length > 100000) {
      return NextResponse.json(
        { error: "HTML content too large. Maximum 100,000 characters." },
        { status: 400 }
      );
    }

    const message = await client.messages.create({
      model: "claude-haiku-4-5-20251001",
      max_tokens: 4096,
      system: SYSTEM_PROMPT,
      messages: [
        {
          role: "user",
          content: `Extract and classify document links from this investor relations page HTML:\n\n${html}`,
        },
      ],
    });

    const responseText =
      message.content[0].type === "text" ? message.content[0].text : "";

    try {
      const parsed = JSON.parse(responseText);
      return NextResponse.json(parsed);
    } catch {
      return NextResponse.json({ raw: responseText });
    }
  } catch (error) {
    const msg = error instanceof Error ? error.message : "Unknown error";
    return NextResponse.json({ error: msg }, { status: 500 });
  }
}

export async function GET() {
  return NextResponse.json({
    name: "document-link-extractor",
    description:
      "Extracts and classifies financial document links from investor relations page HTML using Claude AI",
    usage: "POST with { html: '<html>...</html>' }",
  });
}

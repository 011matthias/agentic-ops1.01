import { NextRequest, NextResponse } from "next/server";
import { getModule } from "@/modules/registry";

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ module: string }> }
) {
  const { module: moduleName } = await params;
  const config = getModule(moduleName);

  if (!config) {
    return NextResponse.json(
      { error: `Module "${moduleName}" not registered` },
      { status: 404 }
    );
  }

  if (!config.enabled) {
    return NextResponse.json(
      { error: `Module "${moduleName}" is not enabled` },
      { status: 403 }
    );
  }

  // Phase 2: Process module webhook payload and store in database
  const payload = await request.json();
  return NextResponse.json({
    received: true,
    module: moduleName,
    timestamp: new Date().toISOString(),
    items: Array.isArray(payload.data) ? payload.data.length : 1,
  });
}

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ module: string }> }
) {
  const { module: moduleName } = await params;
  const config = getModule(moduleName);

  if (!config) {
    return NextResponse.json(
      {
        error: `Module "${moduleName}" not registered`,
        hint: "Register modules in src/modules/registry.ts",
      },
      { status: 404 }
    );
  }

  return NextResponse.json({
    module: config.name,
    description: config.description,
    orchestrator: config.orchestrator,
    enabled: config.enabled,
  });
}

import { NextRequest, NextResponse } from "next/server";
import { eq } from "drizzle-orm";
import { getModule } from "@/modules/registry";
import { db } from "@/lib/db";
import { moduleExecutions, projects } from "@/lib/schema";
import type { ModuleWebhookPayload } from "@/modules/types";

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

  const payload: ModuleWebhookPayload = await request.json();

  // Find the project linked to this module
  const project = await db.query.projects.findFirst({
    where: eq(projects.name, config.projectSlug),
  });

  if (!project) {
    return NextResponse.json(
      { error: `No project found for module "${moduleName}"` },
      { status: 404 }
    );
  }

  const [execution] = await db
    .insert(moduleExecutions)
    .values({
      projectId: project.id,
      moduleName: config.name,
      status: payload.status ?? "success",
      itemCount: payload.itemCount ?? 0,
      durationMs: payload.durationMs ?? null,
      metadata: payload.data ? JSON.stringify(payload.data) : null,
      executedAt: payload.timestamp ? new Date(payload.timestamp) : new Date(),
    })
    .returning();

  return NextResponse.json({
    received: true,
    executionId: execution.id,
    module: moduleName,
    status: execution.status,
    itemCount: execution.itemCount,
    executedAt: execution.executedAt,
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

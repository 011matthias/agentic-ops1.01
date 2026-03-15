import { redirect } from "next/navigation"
import { desc, eq } from "drizzle-orm"
import { auth } from "@/lib/auth"
import { db } from "@/lib/db"
import { clients, files, projects } from "@/lib/schema"
import PageHeader from "@/components/ui/PageHeader"
import EmptyState from "@/components/ui/EmptyState"

export const metadata = { title: "Files" }

function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B"
  const k = 1024
  const sizes = ["B", "KB", "MB", "GB"]
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`
}

function formatDate(date: Date): string {
  return date.toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
  })
}

function mimeLabel(mimeType: string | null): string {
  if (!mimeType) return "File"
  if (mimeType === "application/pdf") return "PDF"
  if (mimeType.startsWith("image/")) return "Image"
  if (
    mimeType === "application/msword" ||
    mimeType ===
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
  )
    return "Doc"
  if (
    mimeType === "application/vnd.ms-excel" ||
    mimeType ===
      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
  )
    return "Sheet"
  if (mimeType === "text/csv") return "CSV"
  if (mimeType.startsWith("video/")) return "Video"
  if (mimeType.startsWith("audio/")) return "Audio"
  if (mimeType === "application/zip" || mimeType === "application/x-zip-compressed")
    return "ZIP"
  return "File"
}

type FileRow = typeof files.$inferSelect & {
  project: typeof projects.$inferSelect | null
}

export default async function FilesPage() {
  const session = await auth()
  if (!session?.user?.id) redirect("/login")

  const client = await db.query.clients.findFirst({
    where: eq(clients.userId, session.user.id),
  })

  const fileList: FileRow[] = client
    ? await db.query.files.findMany({
        where: eq(files.clientId, client.id),
        orderBy: desc(files.createdAt),
        with: {
          project: true,
        },
      })
    : []

  // Group files by project name (or "General" if no project)
  const groups = new Map<string, FileRow[]>()
  for (const file of fileList) {
    const groupName = file.project?.name ?? "General"
    if (!groups.has(groupName)) {
      groups.set(groupName, [])
    }
    groups.get(groupName)!.push(file)
  }

  return (
    <div className="max-w-5xl mx-auto px-4 py-12">
      <PageHeader
        title="Files"
        subtitle="Deliverables and documents shared by your team."
      />

      {fileList.length === 0 ? (
        <EmptyState
          title="No files yet"
          description="Your team will upload deliverables here."
        />
      ) : (
        <div className="space-y-8">
          {Array.from(groups.entries()).map(([groupName, groupFiles]) => (
            <div key={groupName}>
              <h2 className="text-sm font-semibold text-muted uppercase tracking-wide mb-3">
                {groupName}
              </h2>
              <div className="rounded-2xl border border-border bg-white dark:bg-gray-900 overflow-hidden">
                <ul className="divide-y divide-border">
                  {groupFiles.map((file) => (
                    <li
                      key={file.id}
                      className="flex items-center gap-4 px-6 py-4 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
                    >
                      {/* Mime type badge */}
                      <span className="inline-flex items-center justify-center w-10 h-10 rounded-lg bg-gray-100 dark:bg-gray-800 text-xs font-semibold text-muted shrink-0">
                        {mimeLabel(file.mimeType)}
                      </span>

                      {/* Filename + download */}
                      <div className="flex-1 min-w-0">
                        <a
                          href={file.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-sm font-medium text-foreground hover:text-accent truncate block"
                          download={file.filename}
                        >
                          {file.filename}
                        </a>
                        <p className="text-xs text-muted mt-0.5">
                          Uploaded {formatDate(file.createdAt)}
                        </p>
                      </div>

                      {/* File size */}
                      <span className="text-xs text-muted shrink-0">
                        {file.sizeBytes != null ? formatBytes(file.sizeBytes) : "—"}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

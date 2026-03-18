"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import EmptyState from "@/components/ui/EmptyState"
import Card from "@/components/ui/Card"
import Button from "@/components/ui/Button"
import FileUpload from "@/components/ui/FileUpload"

interface FileRecord {
  id: string
  filename: string
  url: string
  sizeBytes: number | null
  mimeType: string | null
  createdAt: string
  project: { id: string; name: string } | null
}

interface FilesTabProps {
  files: FileRecord[]
  clientId: string
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B"
  const k = 1024
  const sizes = ["B", "KB", "MB", "GB"]
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`
}

function mimeLabel(mimeType: string | null): string {
  if (!mimeType) return "File"
  if (mimeType === "application/pdf") return "PDF"
  if (mimeType.startsWith("image/")) return "Image"
  if (mimeType.includes("wordprocessingml") || mimeType === "application/msword") return "Doc"
  if (mimeType.includes("spreadsheetml") || mimeType === "application/vnd.ms-excel") return "Sheet"
  if (mimeType === "text/csv") return "CSV"
  if (mimeType.startsWith("video/")) return "Video"
  if (mimeType.startsWith("audio/")) return "Audio"
  if (mimeType === "application/zip" || mimeType === "application/x-zip-compressed") return "ZIP"
  return "File"
}

export default function FilesTab({ files: fileList, clientId }: FilesTabProps) {
  const router = useRouter()
  const [deleting, setDeleting] = useState<string | null>(null)

  const handleDelete = async (fileId: string) => {
    if (!confirm("Delete this file? This cannot be undone.")) return
    setDeleting(fileId)
    try {
      const res = await fetch(`/api/admin/files/${fileId}`, { method: "DELETE" })
      if (!res.ok) throw new Error("Delete failed")
      router.refresh()
    } catch {
      alert("Failed to delete file")
    } finally {
      setDeleting(null)
    }
  }

  // Group files by project name
  const groups = new Map<string, FileRecord[]>()
  for (const file of fileList) {
    const groupName = file.project?.name ?? "General"
    if (!groups.has(groupName)) groups.set(groupName, [])
    groups.get(groupName)!.push(file)
  }

  return (
    <div className="flex flex-col gap-8">
      {/* Upload section */}
      <Card>
        <h2 className="text-base font-semibold text-foreground mb-4">Upload file</h2>
        <FileUpload
          endpoint="/api/admin/files"
          clientId={clientId}
        />
      </Card>

      {/* File list */}
      {fileList.length === 0 ? (
        <EmptyState
          title="No files yet"
          description="Upload files for this client using the form above."
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
                      <span className="inline-flex items-center justify-center w-10 h-10 rounded-lg bg-gray-100 dark:bg-gray-800 text-xs font-semibold text-muted shrink-0">
                        {mimeLabel(file.mimeType)}
                      </span>
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
                          Uploaded{" "}
                          {new Date(file.createdAt).toLocaleDateString("en-GB", {
                            day: "numeric",
                            month: "short",
                            year: "numeric",
                          })}
                        </p>
                      </div>
                      <span className="text-xs text-muted shrink-0">
                        {file.sizeBytes != null ? formatBytes(file.sizeBytes) : "\u2014"}
                      </span>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDelete(file.id)}
                        disabled={deleting === file.id}
                        className="text-red-500 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20"
                      >
                        {deleting === file.id ? "..." : "Delete"}
                      </Button>
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

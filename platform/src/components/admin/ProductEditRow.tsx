"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import Badge from "@/components/ui/Badge"
import Button from "@/components/ui/Button"

interface Product {
  id: string
  catalogSlug: string
  name: string
  priceUsd: number
  active: boolean
  createdAt: Date | null
}

interface Props {
  product: Product
}

function formatCents(cents: number): string {
  return (cents / 100).toLocaleString("en-US", { style: "currency", currency: "USD" })
}

export default function ProductEditRow({ product }: Props) {
  const router = useRouter()
  const [editing, setEditing] = useState(false)
  const [name, setName] = useState(product.name)
  const [priceUsd, setPriceUsd] = useState(String(product.priceUsd))
  const [active, setActive] = useState(product.active)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSave() {
    setSaving(true)
    setError(null)
    try {
      const res = await fetch(`/api/admin/products/${product.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, priceUsd: Number(priceUsd) }),
      })
      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(data.error ?? "Failed to save")
      }
      setEditing(false)
      router.refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong")
    } finally {
      setSaving(false)
    }
  }

  async function handleActiveToggle(checked: boolean) {
    setActive(checked)
    try {
      const res = await fetch(`/api/admin/products/${product.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ active: checked }),
      })
      if (!res.ok) {
        // Revert on failure
        setActive(!checked)
      } else {
        router.refresh()
      }
    } catch {
      setActive(!checked)
    }
  }

  function handleCancel() {
    setName(product.name)
    setPriceUsd(String(product.priceUsd))
    setEditing(false)
    setError(null)
  }

  if (editing) {
    return (
      <tr className="bg-amber-50 dark:bg-amber-900/10">
        <td className="px-6 py-3">
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full px-3 py-1.5 rounded-lg border border-border bg-white dark:bg-gray-800 text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-accent"
          />
          {error && <p className="text-xs text-red-600 mt-1">{error}</p>}
        </td>
        <td className="px-6 py-3">
          <code className="text-xs text-muted font-mono">{product.catalogSlug}</code>
        </td>
        <td className="px-6 py-3">
          <input
            type="number"
            value={priceUsd}
            onChange={(e) => setPriceUsd(e.target.value)}
            placeholder="cents, e.g. 4900"
            className="w-28 px-3 py-1.5 rounded-lg border border-border bg-white dark:bg-gray-800 text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-accent"
          />
          {Number(priceUsd) > 0 && (
            <p className="text-xs text-muted mt-1">{formatCents(Number(priceUsd))}</p>
          )}
        </td>
        <td className="px-6 py-3">
          <Badge variant={active ? "success" : "warning"}>
            {active ? "active" : "inactive"}
          </Badge>
        </td>
        <td className="px-6 py-3 text-right">
          <div className="flex items-center justify-end gap-2">
            <Button size="sm" onClick={handleSave} disabled={saving || !name.trim()}>
              {saving ? "Saving..." : "Save"}
            </Button>
            <Button size="sm" variant="ghost" onClick={handleCancel} disabled={saving}>
              Cancel
            </Button>
          </div>
        </td>
      </tr>
    )
  }

  return (
    <tr className="hover:bg-gray-50 dark:hover:bg-gray-800/30 transition-colors">
      <td className="px-6 py-4 font-medium text-foreground">{product.name}</td>
      <td className="px-6 py-4">
        <code className="text-xs text-muted font-mono bg-gray-100 dark:bg-gray-800 px-2 py-0.5 rounded">
          {product.catalogSlug}
        </code>
      </td>
      <td className="px-6 py-4 text-foreground">{formatCents(product.priceUsd)}</td>
      <td className="px-6 py-4">
        <div className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={active}
            onChange={(e) => handleActiveToggle(e.target.checked)}
            className="rounded border-gray-300 text-accent focus:ring-accent cursor-pointer"
            aria-label="Active"
          />
          <Badge variant={active ? "success" : "warning"}>
            {active ? "active" : "inactive"}
          </Badge>
        </div>
      </td>
      <td className="px-6 py-4 text-right">
        <Button size="sm" variant="secondary" onClick={() => setEditing(true)}>
          Edit
        </Button>
      </td>
    </tr>
  )
}

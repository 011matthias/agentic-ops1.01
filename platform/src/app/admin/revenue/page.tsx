import { db } from "@/lib/db"
import { purchases, products, users } from "@/lib/schema"
import { eq, sum, count, desc, and, gte } from "drizzle-orm"
import PageHeader from "@/components/ui/PageHeader"
import EmptyState from "@/components/ui/EmptyState"
import StatCard from "@/components/admin/StatCard"
import Badge from "@/components/ui/Badge"
import ProductEditRow from "@/components/admin/ProductEditRow"

export const metadata = { title: "Revenue — Admin" }

function formatCents(cents: number | string | null): string {
  const n = typeof cents === "string" ? parseFloat(cents) : (cents ?? 0)
  return (n / 100).toLocaleString("en-US", { style: "currency", currency: "USD" })
}

export default async function AdminRevenuePage() {
  // All-time revenue (complete purchases)
  const allTimeRevenue = await db
    .select({ total: sum(products.priceUsd) })
    .from(purchases)
    .leftJoin(products, eq(purchases.productId, products.id))
    .where(eq(purchases.status, "complete"))
    .then((r) => r[0]?.total ?? 0)

  // MTD revenue
  const startOfMonth = new Date()
  startOfMonth.setDate(1)
  startOfMonth.setHours(0, 0, 0, 0)

  const mtdRevenue = await db
    .select({ total: sum(products.priceUsd) })
    .from(purchases)
    .leftJoin(products, eq(purchases.productId, products.id))
    .where(and(eq(purchases.status, "complete"), gte(purchases.createdAt, startOfMonth)))
    .then((r) => r[0]?.total ?? 0)

  // Pending purchases count
  const pendingCount = await db
    .select({ count: count() })
    .from(purchases)
    .where(eq(purchases.status, "pending"))
    .then((r) => r[0]?.count ?? 0)

  // All purchases with product + user info
  const allPurchases = await db
    .select({
      id: purchases.id,
      status: purchases.status,
      stripeSessionId: purchases.stripeSessionId,
      createdAt: purchases.createdAt,
      productName: products.name,
      priceUsd: products.priceUsd,
      userEmail: users.email,
    })
    .from(purchases)
    .leftJoin(products, eq(purchases.productId, products.id))
    .leftJoin(users, eq(purchases.userId, users.id))
    .orderBy(desc(purchases.createdAt))

  // All products
  const allProducts = await db
    .select()
    .from(products)
    .orderBy(desc(products.createdAt))

  const statusVariant = (status: string) => {
    if (status === "complete") return "success" as const
    if (status === "refunded") return "error" as const
    return "warning" as const
  }

  return (
    <div className="max-w-5xl mx-auto px-4 py-12">
      <PageHeader title="Revenue" subtitle="All-time purchases and product management" />

      {/* Stats row */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-10">
        <StatCard label="All-time revenue" value={formatCents(allTimeRevenue)} sublabel="completed orders" />
        <StatCard label="This month" value={formatCents(mtdRevenue)} sublabel="MTD completed" />
        <StatCard label="Pending" value={`${pendingCount} order${pendingCount !== 1 ? "s" : ""}`} sublabel="awaiting completion" />
      </div>

      {/* Purchases section */}
      <section className="mb-12">
        <h2 className="text-lg font-semibold text-foreground mb-4">Purchases</h2>

        {allPurchases.length === 0 ? (
          <EmptyState
            title="No purchases yet"
            description="Purchases will appear here once customers complete checkout."
          />
        ) : (
          <div className="rounded-2xl border border-border bg-white dark:bg-gray-900 overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-gray-50 dark:bg-gray-800/50">
                  <th className="text-left px-6 py-3 font-medium text-muted">Date</th>
                  <th className="text-left px-6 py-3 font-medium text-muted">Customer</th>
                  <th className="text-left px-6 py-3 font-medium text-muted">Product</th>
                  <th className="text-left px-6 py-3 font-medium text-muted">Amount</th>
                  <th className="text-left px-6 py-3 font-medium text-muted">Status</th>
                  <th className="text-left px-6 py-3 font-medium text-muted">Stripe</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {allPurchases.map((purchase) => (
                  <tr
                    key={purchase.id}
                    className="hover:bg-gray-50 dark:hover:bg-gray-800/30 transition-colors"
                  >
                    <td className="px-6 py-4 text-muted whitespace-nowrap">
                      {purchase.createdAt
                        ? purchase.createdAt.toLocaleDateString("en-GB", {
                            day: "numeric",
                            month: "short",
                            year: "numeric",
                          })
                        : "—"}
                    </td>
                    <td className="px-6 py-4 text-foreground">
                      {purchase.userEmail ?? (
                        <span className="text-muted italic">Guest</span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-foreground">
                      {purchase.productName ?? <span className="text-muted">—</span>}
                    </td>
                    <td className="px-6 py-4 text-foreground whitespace-nowrap">
                      {purchase.priceUsd != null ? formatCents(purchase.priceUsd) : "—"}
                    </td>
                    <td className="px-6 py-4">
                      <Badge variant={statusVariant(purchase.status)}>
                        {purchase.status}
                      </Badge>
                    </td>
                    <td className="px-6 py-4">
                      {purchase.stripeSessionId ? (
                        <a
                          href={`https://dashboard.stripe.com/payments/${purchase.stripeSessionId}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-accent hover:underline text-sm"
                        >
                          View →
                        </a>
                      ) : (
                        <span className="text-muted">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Products section */}
      <section>
        <h2 className="text-lg font-semibold text-foreground mb-4">Products</h2>

        {allProducts.length === 0 ? (
          <EmptyState
            title="No products yet"
            description="Products will appear here once they are added to the catalog."
          />
        ) : (
          <div className="rounded-2xl border border-border bg-white dark:bg-gray-900 overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-gray-50 dark:bg-gray-800/50">
                  <th className="text-left px-6 py-3 font-medium text-muted">Name</th>
                  <th className="text-left px-6 py-3 font-medium text-muted">Slug</th>
                  <th className="text-left px-6 py-3 font-medium text-muted">Price</th>
                  <th className="text-left px-6 py-3 font-medium text-muted">Status</th>
                  <th className="text-right px-6 py-3 font-medium text-muted">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {allProducts.map((product) => (
                  <ProductEditRow key={product.id} product={product} />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  )
}

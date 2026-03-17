import { desc, eq } from "drizzle-orm"
import { auth } from "@/lib/auth"
import { db } from "@/lib/db"
import { users, clients } from "@/lib/schema"
import PageHeader from "@/components/ui/PageHeader"
import Badge from "@/components/ui/Badge"
import PromoteDialog from "@/components/admin/PromoteDialog"
import RoleSelect from "@/components/admin/RoleSelect"

export const metadata = { title: "Users — Admin" }

const roleBadgeVariant: Record<string, "success" | "warning" | "default"> = {
  admin: "default",
  client: "success",
  prospect: "warning",
}

export default async function AdminUsersPage() {
  const session = await auth()

  const allUsers = await db
    .select({
      id: users.id,
      name: users.name,
      email: users.email,
      role: users.role,
      createdAt: users.createdAt,
      clientId: clients.id,
      companyName: clients.companyName,
    })
    .from(users)
    .leftJoin(clients, eq(clients.userId, users.id))
    .orderBy(desc(users.createdAt))

  const prospects = allUsers.filter((u) => u.role === "prospect")
  const totalUsers = allUsers.length

  return (
    <div className="max-w-5xl mx-auto px-4 py-12">
      <PageHeader
        title="Users"
        subtitle={`${totalUsers} total user${totalUsers !== 1 ? "s" : ""}${prospects.length > 0 ? ` \u00b7 ${prospects.length} pending review` : ""}`}
      />

      {allUsers.length === 0 ? (
        <div className="flex flex-col items-center justify-center text-center rounded-2xl border border-dashed border-border p-12">
          <h3 className="text-lg font-semibold text-foreground mb-2">
            No users yet
          </h3>
          <p className="text-sm text-muted max-w-sm">
            Users will appear here when they sign up via the login page.
          </p>
        </div>
      ) : (
        <div className="rounded-2xl border border-border bg-white dark:bg-gray-900 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-gray-50 dark:bg-gray-800/50">
                <th className="text-left px-6 py-3 font-medium text-muted">
                  User
                </th>
                <th className="text-left px-6 py-3 font-medium text-muted">
                  Role
                </th>
                <th className="text-left px-6 py-3 font-medium text-muted">
                  Company
                </th>
                <th className="text-left px-6 py-3 font-medium text-muted">
                  Joined
                </th>
                <th className="text-left px-6 py-3 font-medium text-muted">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {allUsers.map((user) => {
                const isSelf = user.id === session?.user?.id
                const role = user.role ?? "prospect"

                return (
                  <tr
                    key={user.id}
                    className="hover:bg-gray-50 dark:hover:bg-gray-800/30 transition-colors"
                  >
                    <td className="px-6 py-4">
                      <p className="font-medium text-foreground">
                        {user.name ?? "No name"}
                      </p>
                      <p className="text-xs text-muted mt-0.5">{user.email}</p>
                    </td>
                    <td className="px-6 py-4">
                      <Badge variant={roleBadgeVariant[role] ?? "default"}>
                        {role}
                      </Badge>
                    </td>
                    <td className="px-6 py-4 text-foreground">
                      {user.companyName ?? (
                        <span className="text-muted">-</span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-muted">
                      {user.createdAt
                        ? user.createdAt.toLocaleDateString("en-GB", {
                            day: "numeric",
                            month: "short",
                            year: "numeric",
                          })
                        : "-"}
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        {role === "prospect" && (
                          <PromoteDialog
                            userId={user.id}
                            userName={user.name}
                          />
                        )}
                        <RoleSelect
                          userId={user.id}
                          currentRole={role}
                          isSelf={isSelf}
                        />
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

import type { ReactNode } from "react"
import { auth, signOut } from "@/lib/auth"
import { redirect } from "next/navigation"
import AdminSidebar from "@/components/admin/AdminSidebar"

export default async function AdminLayout({
  children,
}: {
  children: ReactNode
}) {
  const session = await auth()

  if (!session?.user) {
    redirect("/login")
  }

  if (session.user.role !== "admin") {
    redirect("/portal")
  }

  const user = session.user

  async function handleSignOut() {
    "use server"
    await signOut({ redirectTo: "/" })
  }

  return (
    <div className="min-h-screen flex flex-col sm:flex-row">
      <AdminSidebar
        userName={user.name ?? null}
        userEmail={user.email ?? null}
        signOutAction={handleSignOut}
      />
      <main className="flex-1 bg-gray-50 dark:bg-gray-950 min-h-screen">
        {children}
      </main>
    </div>
  )
}

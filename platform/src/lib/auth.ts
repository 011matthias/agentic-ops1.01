import NextAuth from "next-auth"
import Google from "next-auth/providers/google"
import Resend from "next-auth/providers/resend"
import { DrizzleAdapter } from "@auth/drizzle-adapter"
import { db } from "./db"
import { users, accounts, sessions, verificationTokens } from "./schema"
import { notifyAdmin } from "./email"

export const { auth, handlers, signIn, signOut } = NextAuth({
  adapter: DrizzleAdapter(db, {
    usersTable: users,
    accountsTable: accounts,
    sessionsTable: sessions,
    verificationTokensTable: verificationTokens,
  }),
  providers: [
    Google({
      clientId: process.env.AUTH_GOOGLE_ID!,
      clientSecret: process.env.AUTH_GOOGLE_SECRET!,
    }),
    Resend({
      apiKey: process.env.RESEND_API_KEY,
      from: "no-reply@unpauseai.com",
    }),
  ],
  pages: {
    signIn: "/login",
  },
  events: {
    async createUser({ user }) {
      await notifyAdmin(
        `New sign-up: ${user.email}`,
        `A new user signed up on unpauseai.com.\n\nName: ${user.name ?? "(not provided)"}\nEmail: ${user.email}\n\nThey have been assigned the "prospect" role. Visit the admin panel to review and promote them:\nhttps://unpauseai.com/admin/users`
      )
    },
  },
  callbacks: {
    session({ session, user }) {
      if (session.user && user) {
        session.user.id = user.id
        session.user.role = user.role ?? "prospect"
      }
      return session
    },
  },
})

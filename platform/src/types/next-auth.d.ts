import { DefaultSession } from "next-auth"

declare module "next-auth" {
  interface Session {
    user: {
      id: string
      role: "admin" | "client"
    } & DefaultSession["user"]
  }
  interface User {
    role?: "admin" | "client"
  }
}

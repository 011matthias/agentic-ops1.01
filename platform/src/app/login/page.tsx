"use client"

import { useState } from "react"
import { signIn } from "next-auth/react"
import Link from "next/link"

export default function LoginPage() {
  const [email, setEmail] = useState("")
  const [emailSent, setEmailSent] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")

  async function handleGoogleSignIn() {
    setLoading(true)
    setError("")
    try {
      await signIn("google", { callbackUrl: "/auth/redirect" })
    } catch {
      setError("Something went wrong. Please try again.")
      setLoading(false)
    }
  }

  async function handleEmailSignIn(e: React.FormEvent) {
    e.preventDefault()
    if (!email) return
    setLoading(true)
    setError("")
    try {
      const result = await signIn("resend", {
        email,
        redirect: false,
        callbackUrl: "/auth/redirect",
      })
      setLoading(false)
      if (result?.ok) {
        setEmailSent(true)
      } else {
        setError("Failed to send sign-in link. Please try again.")
      }
    } catch {
      setError("Something went wrong. Please try again.")
      setLoading(false)
    }
  }

  if (emailSent) {
    return (
      <div className="min-h-screen flex items-center justify-center px-4 bg-gray-50 dark:bg-gray-950">
        <div className="max-w-sm w-full text-center space-y-5">
          <div className="w-12 h-12 mx-auto rounded-xl bg-blue-500/10 flex items-center justify-center">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#3b82f6" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="2" y="4" width="20" height="16" rx="2" />
              <path d="M22 4l-10 8L2 4" />
            </svg>
          </div>
          <div>
            <h1 className="text-xl font-semibold text-gray-900 dark:text-white">Check your email</h1>
            <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
              We sent a sign-in link to <strong className="text-gray-700 dark:text-gray-300">{email}</strong>
            </p>
          </div>
          <button
            onClick={() => { setEmailSent(false); setLoading(false); setError("") }}
            className="text-sm text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
          >
            Use a different email
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4 bg-gray-50 dark:bg-gray-950">
      <div className="max-w-sm w-full space-y-8">
        {/* Brand mark */}
        <div className="text-center">
          <Link href="/" className="inline-block">
            <span className="text-lg font-semibold tracking-tight text-gray-900 dark:text-white">
              UnpauseAI
            </span>
          </Link>
          <p className="mt-1.5 text-sm text-gray-500 dark:text-gray-400">
            Sign in to your account
          </p>
        </div>

        {/* Card */}
        <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-6 space-y-5 shadow-sm">
          {error && (
            <div className="px-3 py-2 text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-100 dark:border-red-900/30">
              {error}
            </div>
          )}

          {/* Google */}
          <button
            onClick={handleGoogleSignIn}
            disabled={loading}
            className="w-full flex items-center justify-center gap-2.5 px-4 py-2.5 border border-gray-200 dark:border-gray-700 rounded-lg text-sm font-medium text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <svg className="w-4 h-4" viewBox="0 0 24 24">
              <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
              <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
              <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z" />
              <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
            </svg>
            Continue with Google
          </button>

          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-gray-100 dark:border-gray-800" />
            </div>
            <div className="relative flex justify-center text-xs">
              <span className="bg-white dark:bg-gray-900 px-3 text-gray-400 uppercase tracking-wider">or</span>
            </div>
          </div>

          {/* Magic link */}
          <form onSubmit={handleEmailSignIn} className="space-y-3">
            <div>
              <label
                htmlFor="email"
                className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1.5"
              >
                Email address
              </label>
              <input
                id="email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@company.com"
                className="w-full px-3 py-2.5 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500/40 focus:border-blue-500 transition-colors"
              />
            </div>
            <button
              type="submit"
              disabled={loading || !email}
              className="w-full px-4 py-2.5 bg-gray-900 dark:bg-white text-white dark:text-gray-900 rounded-lg text-sm font-medium hover:bg-gray-800 dark:hover:bg-gray-100 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? "Sending..." : "Send sign-in link"}
            </button>
          </form>
        </div>

        <p className="text-center text-xs text-gray-400 leading-relaxed">
          New accounts are reviewed before access is granted.{" "}
          <Link href="/contact" className="text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 transition-colors underline underline-offset-2">
            Need help?
          </Link>
        </p>
      </div>
    </div>
  )
}

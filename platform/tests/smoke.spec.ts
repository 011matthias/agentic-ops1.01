import { test, expect } from "@playwright/test"

/**
 * Smoke tests — screenshot public + auth-gated routes.
 * Run: npx playwright test tests/smoke.spec.ts
 * Screenshots saved to: test-results/
 */

test("home page loads", async ({ page }) => {
  await page.goto("/")
  await expect(page).toHaveTitle(/UnpauseAI/)
  await page.screenshot({ path: "test-results/home.png", fullPage: true })
})

test("services page loads", async ({ page }) => {
  await page.goto("/services")
  await page.screenshot({ path: "test-results/services.png", fullPage: true })
})

test("about page loads", async ({ page }) => {
  await page.goto("/about")
  await page.screenshot({ path: "test-results/about.png", fullPage: true })
})

test("contact page loads", async ({ page }) => {
  await page.goto("/contact")
  await page.screenshot({ path: "test-results/contact.png", fullPage: true })
})

test("login page loads", async ({ page }) => {
  await page.goto("/login")
  await page.screenshot({ path: "test-results/login.png", fullPage: true })
})

test("portal redirects to login when unauthenticated", async ({ page }) => {
  await page.goto("/portal")
  // Should redirect to /login (next-auth behaviour)
  await expect(page).toHaveURL(/login/)
  await page.screenshot({ path: "test-results/portal-redirect.png" })
})

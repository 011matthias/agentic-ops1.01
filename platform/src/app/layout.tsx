import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { Analytics } from "@vercel/analytics/react";
import Header from "@/components/Header";
import Footer from "@/components/Footer";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: {
    default: "UnpausAI — Automation Solutions",
    template: "%s | UnpausAI",
  },
  description:
    "We build automations that run your business. Lead follow-up, CRM sync, sales dashboards, and custom workflows — connected to your existing tools.",
  openGraph: {
    title: "UnpausAI — Automation Solutions",
    description:
      "We build automations that run your business. Lead follow-up, CRM sync, sales dashboards, and custom workflows.",
    url: "https://unpauseai.com",
    siteName: "UnpausAI",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        <Header />
        <main>{children}</main>
        <Footer />
        <Analytics />
      </body>
    </html>
  );
}

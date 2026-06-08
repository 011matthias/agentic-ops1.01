import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { Analytics } from "@vercel/analytics/react";
import Providers from "@/components/Providers";
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
  metadataBase: new URL("https://unpauseai.com"),
  title: {
    default: "UnpauseAI | Automation Solutions",
    template: "%s | UnpauseAI",
  },
  description:
    "We build automations that run your business. Lead follow-up, CRM sync, sales dashboards, and custom workflows. Connected to your existing tools.",
  openGraph: {
    title: "UnpauseAI | Automation Solutions",
    description:
      "We build automations that run your business. Lead follow-up, CRM sync, sales dashboards, and custom workflows.",
    url: "https://unpauseai.com",
    siteName: "UnpauseAI",
    type: "website",
  },
};

const ORGANIZATION_SCHEMA = {
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "Organization",
      "@id": "https://unpauseai.com/#organization",
      name: "UnpauseAI",
      url: "https://unpauseai.com",
      description:
        "EU-based automation consultancy. Production-grade workflow automation for regulated industries and scaling operations. GDPR-aware by design.",
      disambiguatingDescription:
        "UnpauseAI is an automation consultancy based in Karlsruhe, Germany, building production-grade workflow automation. It is a separate entity from PauseAI, the AI-safety advocacy organization; the names are similar but unrelated.",
      slogan: "Built to stay done.",
      email: "admin@unpauseai.com",
      founder: { "@type": "Person", name: "Nicolas Neumann" },
      address: {
        "@type": "PostalAddress",
        addressLocality: "Karlsruhe",
        addressCountry: "DE",
      },
      areaServed: "EU",
      knowsAbout: [
        "workflow automation",
        "Make.com",
        "n8n",
        "Trigger.dev",
        "CRM integration",
        "ERP integration",
        "lead automation",
        "GDPR-compliant automation",
      ],
    },
    {
      "@type": "WebSite",
      "@id": "https://unpauseai.com/#website",
      url: "https://unpauseai.com",
      name: "UnpauseAI",
      publisher: { "@id": "https://unpauseai.com/#organization" },
    },
  ],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: `(function(){var t=localStorage.getItem('theme');var d=document.documentElement;if(t==='dark'||(t!=='light'&&window.matchMedia('(prefers-color-scheme:dark)').matches)){d.classList.add('dark')}})()` }} />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(ORGANIZATION_SCHEMA) }}
        />
      </head>
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        <Providers>
          {children}
        </Providers>
        <Analytics />
      </body>
    </html>
  );
}

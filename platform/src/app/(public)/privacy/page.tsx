import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Privacy Policy",
  description: "Privacy Policy for UnpauseAI automation services.",
};

export default function PrivacyPage() {
  return (
    <div className="mx-auto max-w-3xl px-6 py-20">
      <h1 className="mb-8 text-3xl font-bold tracking-tight sm:text-4xl">
        Privacy Policy
      </h1>
      <p className="mb-8 text-sm text-muted">Last updated: March 23, 2026</p>

      <div className="space-y-8 leading-relaxed text-muted">
        <section>
          <h2 className="mb-3 text-lg font-semibold text-foreground">
            1. Information We Collect
          </h2>
          <p className="mb-3">
            We collect information that you provide directly when using our
            services:
          </p>
          <ul className="list-disc space-y-1 pl-6">
            <li>
              <strong className="text-foreground">Account information:</strong>{" "}
              Name and email address when you sign in via Google or magic link.
            </li>
            <li>
              <strong className="text-foreground">Contact form data:</strong>{" "}
              Name, email, company name, and message content when you submit our
              contact form.
            </li>
            <li>
              <strong className="text-foreground">Project data:</strong>{" "}
              Information related to your automation projects, including
              configurations, integration credentials, and business data
              processed by your workflows.
            </li>
          </ul>
        </section>

        <section>
          <h2 className="mb-3 text-lg font-semibold text-foreground">
            2. How We Use Your Information
          </h2>
          <ul className="list-disc space-y-1 pl-6">
            <li>To provide and maintain our automation services</li>
            <li>To authenticate you and manage your portal access</li>
            <li>To communicate with you about your projects</li>
            <li>To respond to your inquiries and support requests</li>
            <li>To improve our services and website</li>
          </ul>
        </section>

        <section>
          <h2 className="mb-3 text-lg font-semibold text-foreground">
            3. Third-Party Services
          </h2>
          <p className="mb-3">We use the following third-party services:</p>
          <ul className="list-disc space-y-1 pl-6">
            <li>
              <strong className="text-foreground">Google OAuth:</strong> For
              account authentication. Subject to{" "}
              <a
                href="https://policies.google.com/privacy"
                className="text-accent hover:text-accent-light"
                target="_blank"
                rel="noopener noreferrer"
              >
                Google&rsquo;s Privacy Policy
              </a>
              .
            </li>
            <li>
              <strong className="text-foreground">Resend:</strong> For sending
              authentication emails (magic links). Subject to{" "}
              <a
                href="https://resend.com/legal/privacy-policy"
                className="text-accent hover:text-accent-light"
                target="_blank"
                rel="noopener noreferrer"
              >
                Resend&rsquo;s Privacy Policy
              </a>
              .
            </li>
            <li>
              <strong className="text-foreground">Vercel:</strong> For hosting
              and analytics. Subject to{" "}
              <a
                href="https://vercel.com/legal/privacy-policy"
                className="text-accent hover:text-accent-light"
                target="_blank"
                rel="noopener noreferrer"
              >
                Vercel&rsquo;s Privacy Policy
              </a>
              .
            </li>
            <li>
              <strong className="text-foreground">Neon:</strong> For database
              hosting. Subject to{" "}
              <a
                href="https://neon.tech/privacy"
                className="text-accent hover:text-accent-light"
                target="_blank"
                rel="noopener noreferrer"
              >
                Neon&rsquo;s Privacy Policy
              </a>
              .
            </li>
          </ul>
        </section>

        <section>
          <h2 className="mb-3 text-lg font-semibold text-foreground">
            4. Cookies and Local Storage
          </h2>
          <p>
            We use browser localStorage to persist your theme preference
            (dark/light mode) and authentication session. We use Vercel Analytics
            for anonymous usage statistics. We do not use tracking cookies or
            third-party advertising trackers.
          </p>
        </section>

        <section>
          <h2 className="mb-3 text-lg font-semibold text-foreground">
            5. Data Retention
          </h2>
          <p>
            We retain your account information for as long as your account is
            active. Project data is retained for the duration of our engagement
            and for a reasonable period afterward for support purposes. You may
            request deletion of your data at any time by contacting us.
          </p>
        </section>

        <section>
          <h2 className="mb-3 text-lg font-semibold text-foreground">
            6. Data Security
          </h2>
          <p>
            We implement appropriate technical and organizational measures to
            protect your personal data. All data is transmitted over HTTPS and
            stored in encrypted databases. However, no method of transmission
            over the Internet is 100% secure.
          </p>
        </section>

        <section>
          <h2 className="mb-3 text-lg font-semibold text-foreground">
            7. Your Rights
          </h2>
          <p className="mb-3">You have the right to:</p>
          <ul className="list-disc space-y-1 pl-6">
            <li>Access the personal data we hold about you</li>
            <li>Request correction of inaccurate data</li>
            <li>Request deletion of your data</li>
            <li>Withdraw consent for data processing</li>
            <li>Request a copy of your data in a portable format</li>
          </ul>
        </section>

        <section>
          <h2 className="mb-3 text-lg font-semibold text-foreground">
            8. Changes to This Policy
          </h2>
          <p>
            We may update this privacy policy from time to time. Material
            changes will be communicated via email to registered users.
          </p>
        </section>

        <section>
          <h2 className="mb-3 text-lg font-semibold text-foreground">
            9. Contact
          </h2>
          <p>
            For privacy-related questions or to exercise your rights, contact us
            at{" "}
            <a
              href="mailto:admin@unpauseai.com"
              className="text-accent hover:text-accent-light"
            >
              admin@unpauseai.com
            </a>
            .
          </p>
        </section>
      </div>
    </div>
  );
}

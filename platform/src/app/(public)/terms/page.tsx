import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Terms of Service",
  description: "Terms of Service for UnpauseAI automation services.",
};

export default function TermsPage() {
  return (
    <div className="mx-auto max-w-3xl px-6 py-20">
      <h1 className="mb-8 text-3xl font-bold tracking-tight sm:text-4xl">
        Terms of Service
      </h1>
      <p className="mb-8 text-sm text-muted">Last updated: March 23, 2026</p>

      <div className="space-y-8 leading-relaxed text-muted">
        <section>
          <h2 className="mb-3 text-lg font-semibold text-foreground">
            1. Agreement to Terms
          </h2>
          <p>
            By accessing or using the services provided by UnpauseAI
            (&ldquo;we&rdquo;, &ldquo;us&rdquo;, or &ldquo;our&rdquo;),
            including our website at unpauseai.com and client portal, you agree
            to be bound by these Terms of Service. If you do not agree, do not
            use our services.
          </p>
        </section>

        <section>
          <h2 className="mb-3 text-lg font-semibold text-foreground">
            2. Services
          </h2>
          <p>
            UnpauseAI provides custom automation consulting and development
            services. We build, deploy, and maintain automated workflows using
            third-party orchestration platforms (such as Make.com, n8n, and
            Trigger.dev) on behalf of our clients. The specific scope of each
            engagement is defined in the project proposal agreed upon between you
            and UnpauseAI.
          </p>
        </section>

        <section>
          <h2 className="mb-3 text-lg font-semibold text-foreground">
            3. User Accounts
          </h2>
          <p>
            To access the client portal, you may be required to create an
            account. You are responsible for maintaining the confidentiality of
            your account credentials and for all activities that occur under your
            account. You agree to notify us immediately of any unauthorized
            access.
          </p>
        </section>

        <section>
          <h2 className="mb-3 text-lg font-semibold text-foreground">
            4. Intellectual Property
          </h2>
          <p>
            Upon full payment, automation workflows and code developed
            specifically for your project are delivered to you as independent
            systems. You own the workflows we build for you. UnpauseAI retains
            the right to use general methodologies, techniques, and know-how
            developed during the engagement.
          </p>
        </section>

        <section>
          <h2 className="mb-3 text-lg font-semibold text-foreground">
            5. Payment
          </h2>
          <p>
            Payment terms are specified in each project proposal. Unless
            otherwise agreed, invoices are due within 14 days of receipt. We
            reserve the right to suspend services for overdue payments.
          </p>
        </section>

        <section>
          <h2 className="mb-3 text-lg font-semibold text-foreground">
            6. Limitation of Liability
          </h2>
          <p>
            To the maximum extent permitted by applicable law, UnpauseAI shall
            not be liable for any indirect, incidental, special, consequential,
            or punitive damages, or any loss of profits or revenues, whether
            incurred directly or indirectly. Our total liability for any claim
            arising from or related to these terms shall not exceed the amount
            you paid us in the 12 months preceding the claim.
          </p>
        </section>

        <section>
          <h2 className="mb-3 text-lg font-semibold text-foreground">
            7. Third-Party Services
          </h2>
          <p>
            Our automations integrate with third-party platforms and services. We
            are not responsible for the availability, reliability, or terms of
            those third-party services. Your use of third-party platforms is
            subject to their respective terms.
          </p>
        </section>

        <section>
          <h2 className="mb-3 text-lg font-semibold text-foreground">
            8. Termination
          </h2>
          <p>
            Either party may terminate an engagement with 30 days written
            notice. Upon termination, we will deliver all completed work and
            documentation. Fees for work completed prior to termination remain
            due.
          </p>
        </section>

        <section>
          <h2 className="mb-3 text-lg font-semibold text-foreground">
            9. Changes to Terms
          </h2>
          <p>
            We may update these terms from time to time. Material changes will
            be communicated via email to registered users. Continued use of our
            services after changes constitutes acceptance of the updated terms.
          </p>
        </section>

        <section>
          <h2 className="mb-3 text-lg font-semibold text-foreground">
            10. Contact
          </h2>
          <p>
            Questions about these terms? Contact us at{" "}
            <a
              href="mailto:nicolas.neumann@unpauseai.com"
              className="text-accent hover:text-accent-light"
            >
              nicolas.neumann@unpauseai.com
            </a>
            .
          </p>
        </section>
      </div>
    </div>
  );
}

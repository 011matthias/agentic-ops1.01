export default function Home() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center px-6">
      <main className="flex max-w-2xl flex-col items-center gap-8 text-center">
        <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">
          UnpausAI
        </h1>
        <p className="text-lg text-muted leading-relaxed">
          Custom automation solutions that save you time and scale your
          operations. We build workflows tailored to your business.
        </p>
        <a
          href="mailto:hello@unpauseai.com"
          className="rounded-full bg-accent px-6 py-3 text-sm font-medium text-white transition-colors hover:bg-accent-light"
        >
          Get in Touch
        </a>
      </main>
    </div>
  );
}

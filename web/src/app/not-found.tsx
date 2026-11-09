import Link from "next/link";

export default function NotFound() {
  return (
    <main className="mx-auto flex min-h-dvh max-w-sm flex-col items-center justify-center gap-3 px-5 text-center">
      <h1 className="page-title">Not found</h1>
      <p className="text-sm text-ink-lo">That page doesn&apos;t exist.</p>
      <Link href="/" className="font-semibold text-accent">
        Back to your war room
      </Link>
    </main>
  );
}

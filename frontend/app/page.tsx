import Link from "next/link";

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-8">
      <div className="glass-card flex flex-col items-center gap-6 px-10 py-12 text-center">
        <div className="flex flex-col gap-1">
          <h1 className="text-[28px] font-semibold tracking-[-0.02em]">Quiz Dr</h1>
          <p className="text-[15px] text-[var(--muted)]">Midwifery exam practice bank</p>
        </div>
        <div className="flex gap-3">
          <Link href="/quiz" className="btn-primary inline-flex items-center justify-center">
            Take Quiz
          </Link>
        </div>
      </div>
    </main>
  );
}

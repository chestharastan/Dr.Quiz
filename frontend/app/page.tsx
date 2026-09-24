import Link from "next/link";
import BrandMark from "@/components/BrandMark";

export default function Home() {
  return (
    <main className="flex min-h-dvh flex-col items-center justify-center px-4 py-8">
      <div className="glass-card flex flex-col items-center gap-6 px-10 py-12 text-center">
        <BrandMark size="lg" />
        <div className="flex flex-col gap-1">
          <h1 className="text-[28px] font-bold tracking-[-0.025em]">Quiz Dr</h1>
          <p className="text-[15px] text-[var(--muted)]">Midwifery exam practice bank</p>
        </div>
        <div className="flex gap-3">
          <Link href="/quiz" className="btn-primary">
            Take Quiz
          </Link>
        </div>
      </div>
    </main>
  );
}

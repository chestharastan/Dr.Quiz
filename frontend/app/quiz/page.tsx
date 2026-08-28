"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { fetchMe, logout, type AuthUser } from "@/lib/api";

export default function QuizHubPage() {
  const router = useRouter();
  const [user, setUser] = useState<AuthUser | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        setUser(await fetchMe());
      } catch {
        router.push("/login");
        return;
      }
      setReady(true);
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleLogout() {
    await logout();
    router.push("/login");
  }

  if (!ready || !user) {
    return <main className="mx-auto flex max-w-xl flex-col gap-6 p-8" />;
  }

  return (
    <main className="mx-auto flex w-full max-w-xl flex-col gap-6 p-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-[20px] font-semibold tracking-[-0.02em]">Quiz</h1>
          <p className="text-[13px] text-[var(--muted)]">Welcome, {user.username}</p>
        </div>
        <button
          onClick={handleLogout}
          className="text-[13px] font-medium text-[var(--muted)] hover:text-[var(--foreground)]"
        >
          Log out
        </button>
      </div>

      <div className="flex flex-col gap-4 sm:flex-row">
        <Link href="/quiz/text" className="glass-card flex flex-1 flex-col gap-2 p-6 hover:opacity-90">
          <span className="text-[15px] font-semibold">Text Quiz</span>
          <span className="text-[13px] text-[var(--muted)]">
            Multiple-choice questions from the curated question bank.
          </span>
        </Link>

        <Link href="/quiz/image" className="glass-card flex flex-1 flex-col gap-2 p-6 hover:opacity-90">
          <span className="text-[15px] font-semibold">Image Quiz</span>
          <span className="text-[13px] text-[var(--muted)]">
            Answer questions shown as scanned exam images.
          </span>
        </Link>

        <Link href="/quiz/qa" className="glass-card flex flex-1 flex-col gap-2 p-6 hover:opacity-90">
          <span className="text-[15px] font-semibold">QA Image Quiz</span>
          <span className="text-[13px] text-[var(--muted)]">
            Question and each choice as separate images, in randomized order.
          </span>
        </Link>
      </div>
    </main>
  );
}

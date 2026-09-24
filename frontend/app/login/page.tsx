"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { login } from "@/lib/api";
import BrandMark from "@/components/BrandMark";

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      const user = await login(username, password);
      router.push(user.role === "admin" ? "/admin" : "/quiz");
      router.refresh();
    } catch {
      setError("Invalid email or password.");
      setSubmitting(false);
    }
  }

  return (
    <main className="flex min-h-dvh flex-col items-center justify-center px-4 py-8">
      <form onSubmit={handleSubmit} className="glass-card flex w-full max-w-sm flex-col gap-5 p-8">
        <div className="flex flex-col items-center gap-3 text-center">
          <BrandMark size="lg" />
          <div>
            <h1 className="text-[24px] font-bold tracking-[-0.025em]">Quiz Dr</h1>
            <p className="text-[14px] text-[var(--muted)]">Sign in to continue</p>
          </div>
        </div>

        <label className="flex flex-col gap-1.5">
          <span className="text-[13px] font-medium text-[var(--muted)]">Email</span>
          <input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoFocus
            inputMode="email"
            placeholder="name@gmail.com"
            autoComplete="username"
            autoCapitalize="none"
            autoCorrect="off"
            spellCheck={false}
            className="input-field"
          />
        </label>

        <label className="flex flex-col gap-1.5">
          <span className="text-[13px] font-medium text-[var(--muted)]">Password</span>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="input-field"
          />
        </label>

        {error && <p className="text-[13px] text-incorrect">{error}</p>}

        <button
          type="submit"
          disabled={submitting || !username || !password}
          className="btn-primary inline-flex items-center justify-center"
        >
          {submitting ? "Signing in…" : "Sign in"}
        </button>
      </form>
    </main>
  );
}

"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { login } from "@/lib/api";

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
      setError("Invalid username or password.");
      setSubmitting(false);
    }
  }

  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-8">
      <form onSubmit={handleSubmit} className="glass-card flex w-full max-w-sm flex-col gap-5 p-8">
        <div className="flex flex-col gap-1 text-center">
          <h1 className="text-[22px] font-semibold tracking-[-0.02em]">Quiz Dr</h1>
          <p className="text-[13px] text-[var(--muted)]">Sign in to continue</p>
        </div>

        <label className="flex flex-col gap-1.5">
          <span className="text-[13px] font-medium text-[var(--muted)]">Username</span>
          <input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoFocus
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

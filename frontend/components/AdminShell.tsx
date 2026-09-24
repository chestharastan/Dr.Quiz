"use client";

import Link from "next/link";
import type { AuthUser } from "@/lib/api";
import BrandMark from "@/components/BrandMark";
import { LogoutIcon, PlayIcon, QuestionsIcon, TasksIcon, UsersIcon } from "@/components/icons";

export type AdminTab = "questions" | "users" | "tasks";

const TABS = [
  { id: "questions", label: "Questions", Icon: QuestionsIcon },
  { id: "users", label: "Users", Icon: UsersIcon },
  { id: "tasks", label: "Tasks", Icon: TasksIcon },
] as const;

// Sidebar on tablets and computers; a top bar plus an iOS-style tab bar on phones.
export default function AdminShell({
  user,
  tab,
  onTabChange,
  onLogout,
  children,
}: {
  user: AuthUser;
  tab: AdminTab;
  onTabChange: (tab: AdminTab) => void;
  onLogout: () => void;
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-dvh w-full flex-col">
      <aside className="sidebar glass-bar hidden md:flex md:flex-col">
        <div className="flex items-center gap-2.5 px-5 pt-6 pb-5">
          <BrandMark />
          <div className="leading-tight">
            <p className="text-[15px] font-semibold">Quiz Dr</p>
            <p className="text-[12px] text-[var(--muted)]">Admin</p>
          </div>
        </div>

        <nav aria-label="Admin sections" className="flex flex-col gap-0.5 px-3">
          {TABS.map(({ id, label, Icon }) => (
            <button
              key={id}
              type="button"
              onClick={() => onTabChange(id)}
              aria-current={tab === id ? "page" : undefined}
              className="nav-item"
            >
              <Icon />
              {label}
            </button>
          ))}
          <div className="mx-2 my-2 h-px bg-[var(--hairline)]" />
          <Link href="/quiz" className="nav-item">
            <PlayIcon />
            Take a quiz
          </Link>
        </nav>

        <div className="mt-auto flex items-center gap-2.5 border-t border-[var(--hairline)] px-4 py-4">
          <span className="avatar">{(user.name || user.username).slice(0, 1).toUpperCase()}</span>
          <div className="min-w-0 flex-1 leading-tight">
            <p className="truncate text-[13px] font-medium">{user.name || user.username}</p>
            <p className="truncate text-[12px] text-[var(--muted)]">{user.name ? user.username : "Administrator"}</p>
          </div>
          <button type="button" onClick={onLogout} aria-label="Log out" title="Log out" className="icon-button">
            <LogoutIcon />
          </button>
        </div>
      </aside>

      <header className="topbar glass-bar md:hidden">
        <div className="flex h-13 items-center justify-between px-4">
          <div className="flex items-center gap-2.5">
            <BrandMark />
            <span className="text-[16px] font-semibold">Quiz Dr</span>
          </div>
          <button type="button" onClick={onLogout} aria-label="Log out" title="Log out" className="icon-button">
            <LogoutIcon />
          </button>
        </div>
      </header>

      <main className="admin-main flex-1">
        <div className="mx-auto w-full max-w-6xl px-4 py-5 sm:px-6 md:px-8 md:py-8">{children}</div>
      </main>

      <nav aria-label="Admin sections" className="tabbar glass-bar grid grid-cols-4 md:hidden">
        {TABS.map(({ id, label, Icon }) => (
          <button
            key={id}
            type="button"
            onClick={() => onTabChange(id)}
            aria-current={tab === id ? "page" : undefined}
            className="tab-item"
          >
            <Icon />
            {label}
          </button>
        ))}
        <Link href="/quiz" className="tab-item">
          <PlayIcon />
          Quiz
        </Link>
      </nav>
    </div>
  );
}

"use client";

import { useEffect, useRef, useState } from "react";
import type { AdminQuestion } from "@/lib/api";
import StatusPill from "@/components/StatusPill";

const HEIGHT_KEY = "quizdr:admin-table-height";
const MIN_HEIGHT = 240;
const DEFAULT_HEIGHT = 560;

function savedHeight() {
  try {
    const height = Number(localStorage.getItem(HEIGHT_KEY));
    if (height >= MIN_HEIGHT) return height;
  } catch {
    // storage blocked: use the default
  }
  return DEFAULT_HEIGHT;
}

function DotsIcon() {
  return (
    <svg viewBox="0 0 20 20" className="h-4 w-4" fill="currentColor" aria-hidden="true">
      <circle cx="10" cy="4" r="1.7" />
      <circle cx="10" cy="10" r="1.7" />
      <circle cx="10" cy="16" r="1.7" />
    </svg>
  );
}

type Menu = { question: AdminQuestion; right: number; top?: number; bottom?: number };

export default function AdminQuestionTable({
  questions,
  scrollResetKey,
  onView,
  onEdit,
  onDelete,
}: {
  questions: AdminQuestion[];
  scrollResetKey: string;
  onView: (question: AdminQuestion) => void;
  onEdit: (question: AdminQuestion) => void;
  onDelete: (question: AdminQuestion) => void;
}) {
  const [height, setHeight] = useState(savedHeight);
  const [menu, setMenu] = useState<Menu | null>(null);
  const scrollBox = useRef<HTMLDivElement>(null);
  const drag = useRef<{ y: number; height: number } | null>(null);

  // A new page starts at its first row.
  useEffect(() => {
    scrollBox.current?.scrollTo({ top: 0 });
  }, [scrollResetKey]);

  // Close the row menu on any outside press, scroll, resize or Escape.
  useEffect(() => {
    if (!menu) return;
    const close = () => setMenu(null);
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") close();
    };
    window.addEventListener("pointerdown", close);
    window.addEventListener("scroll", close, true);
    window.addEventListener("resize", close);
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("pointerdown", close);
      window.removeEventListener("scroll", close, true);
      window.removeEventListener("resize", close);
      window.removeEventListener("keydown", onKey);
    };
  }, [menu]);

  function toggleMenu(question: AdminQuestion, button: HTMLElement) {
    if (menu?.question.id === question.id) {
      setMenu(null);
      return;
    }
    // The menu is fixed to the viewport so the scrolling table can't clip it; open upwards near the bottom.
    const rect = button.getBoundingClientRect();
    const right = window.innerWidth - rect.right;
    setMenu(
      rect.bottom + 150 > window.innerHeight
        ? { question, right, bottom: window.innerHeight - rect.top + 4 }
        : { question, right, top: rect.bottom + 4 }
    );
  }

  function choose(action: (question: AdminQuestion) => void) {
    if (!menu) return;
    setMenu(null);
    action(menu.question);
  }

  function endDrag() {
    if (!drag.current) return;
    drag.current = null;
    try {
      localStorage.setItem(HEIGHT_KEY, String(height));
    } catch {
      // storage blocked: the height just isn't remembered
    }
  }

  if (questions.length === 0) {
    return (
      <div className="glass-card flex flex-col items-center gap-1 px-6 py-12 text-center">
        <p className="text-[15px] font-semibold">No questions found</p>
        <p className="text-[13px] text-[var(--muted)]">Try another search, source or question number.</p>
      </div>
    );
  }

  const dotsButton = (q: AdminQuestion) => (
    <button
      type="button"
      aria-label={`Actions for question ${q.question_number}`}
      aria-haspopup="menu"
      aria-expanded={menu?.question.id === q.id}
      onPointerDown={(e) => e.stopPropagation()}
      onKeyDown={(e) => e.stopPropagation()}
      onClick={(e) => {
        e.stopPropagation(); // the row itself opens View
        toggleMenu(q, e.currentTarget);
      }}
      className="dots-button shrink-0"
    >
      <DotsIcon />
    </button>
  );

  return (
    <div className="flex flex-col">
      <div ref={scrollBox} style={{ "--table-height": `${height}px` } as React.CSSProperties} className="table-box glass-card">
        {/* Phone: a list like iOS Settings; tap a row to view it */}
        <ul className="sm:hidden">
          {questions.map((q) => (
            <li key={q.id} onClick={() => onView(q)} className="list-row flex items-start gap-3 py-3 pr-2 pl-4">
              <span className="answer-pill mt-0.5">{q.correct_answer}</span>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2 text-[12px] text-[var(--muted)]">
                  <span className="truncate">
                    {q.source_file} · #{q.question_number}
                  </span>
                  <StatusPill question={q} />
                </div>
                <p className="mt-1 text-[15px] leading-snug">{q.question_text}</p>
              </div>
              {dotsButton(q)}
            </li>
          ))}
        </ul>

        {/* Tablet/desktop: table; click a row to view it */}
        <table className="data-table is-clickable hidden w-full text-[14px] sm:table">
          <thead>
            <tr className="text-left">
              <th className="whitespace-nowrap">Source</th>
              <th>#</th>
              <th className="w-full">Question</th>
              <th className="text-center">Answer</th>
              <th>Status</th>
              <th>
                <span className="sr-only">Actions</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {questions.map((q) => (
              <tr
                key={q.id}
                tabIndex={0}
                onClick={() => onView(q)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") onView(q);
                }}
              >
                <td className="whitespace-nowrap text-[13px] text-[var(--muted)]">{q.source_file}</td>
                <td className="text-[var(--muted)] tabular-nums">{q.question_number}</td>
                <td className="leading-snug">{q.question_text}</td>
                <td className="text-center">
                  <span className="answer-pill">{q.correct_answer}</span>
                </td>
                <td>
                  <StatusPill question={q} />
                </td>
                <td className="text-right">{dotsButton(q)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div
        role="separator"
        aria-orientation="horizontal"
        aria-label="Drag to change the table height"
        title="Drag to change the table height"
        className="resize-handle"
        onPointerDown={(e) => {
          e.preventDefault();
          e.currentTarget.setPointerCapture(e.pointerId);
          drag.current = { y: e.clientY, height };
        }}
        onPointerMove={(e) => {
          if (drag.current) setHeight(Math.max(MIN_HEIGHT, drag.current.height + e.clientY - drag.current.y));
        }}
        onPointerUp={endDrag}
        onPointerCancel={endDrag}
      >
        <span />
      </div>

      {menu && (
        <div
          role="menu"
          className="row-menu"
          style={{ top: menu.top, bottom: menu.bottom, right: menu.right }}
          onPointerDown={(e) => e.stopPropagation()}
        >
          <button type="button" role="menuitem" className="row-menu-item" onClick={() => choose(onView)}>
            View
          </button>
          <button type="button" role="menuitem" className="row-menu-item" onClick={() => choose(onEdit)}>
            Edit
          </button>
          {menu.question.is_active && (
            <button
              type="button"
              role="menuitem"
              className="row-menu-item text-incorrect"
              onClick={() => choose(onDelete)}
            >
              Delete
            </button>
          )}
        </div>
      )}
    </div>
  );
}

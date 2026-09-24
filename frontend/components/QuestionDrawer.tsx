"use client";

import { useEffect, useRef, useState } from "react";
import { updateAdminQuestion, type AdminQuestion } from "@/lib/api";
import StatusPill from "@/components/StatusPill";

const LETTERS = ["A", "B", "C", "D"] as const;
type Letter = (typeof LETTERS)[number];
type ChoiceKey = "choice_a" | "choice_b" | "choice_c" | "choice_d";

const choiceKey = (letter: Letter) => `choice_${letter.toLowerCase()}` as ChoiceKey;

type Draft = Pick<AdminQuestion, "question_text" | ChoiceKey | "correct_answer" | "needs_review" | "is_active">;

function toDraft(q: AdminQuestion): Draft {
  return {
    question_text: q.question_text,
    choice_a: q.choice_a,
    choice_b: q.choice_b,
    choice_c: q.choice_c,
    choice_d: q.choice_d,
    correct_answer: q.correct_answer,
    needs_review: q.needs_review,
    is_active: q.is_active,
  };
}

function QuestionView({ question }: { question: AdminQuestion }) {
  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap items-center gap-2">
        <StatusPill question={question} />
        <span className="text-[13px] text-[var(--muted)]">Correct answer: {question.correct_answer}</span>
      </div>
      <p className="text-[17px] font-semibold leading-snug">{question.question_text}</p>
      <div className="flex flex-col gap-2">
        {LETTERS.map((letter) => {
          const correct = letter === question.correct_answer;
          return (
            <div key={letter} className={`answer-row ${correct ? "answer-row-correct" : ""}`}>
              <span className="choice-letter">{letter}</span>
              <span className="flex-1">{question[choiceKey(letter)]}</span>
              {correct && <span className="shrink-0 text-[13px] font-semibold text-correct">Correct</span>}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function QuestionForm({
  question,
  onDirtyChange,
  onSaved,
  onCancel,
}: {
  question: AdminQuestion;
  onDirtyChange: (dirty: boolean) => void;
  onSaved: (question: AdminQuestion) => void;
  onCancel: () => void;
}) {
  const [draft, setDraft] = useState(() => toDraft(question));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const original = toDraft(question);
  const dirty = (Object.keys(draft) as (keyof Draft)[]).some((k) => draft[k] !== original[k]);
  const texts = [draft.question_text, ...LETTERS.map((l) => draft[choiceKey(l)])];
  const complete = texts.every((t) => t.trim() !== "");

  useEffect(() => {
    onDirtyChange(dirty);
  }, [dirty, onDirtyChange]);

  function set<K extends keyof Draft>(key: K, value: Draft[K]) {
    setDraft((d) => ({ ...d, [key]: value }));
  }

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      onSaved(await updateAdminQuestion(question.id, draft));
    } catch (err) {
      setError(String(err));
      setSaving(false);
    }
  }

  return (
    <form onSubmit={save} className="flex flex-col gap-5">
      <label className="flex flex-col gap-1.5">
        <span className="text-[13px] font-medium text-[var(--muted)]">Question</span>
        <textarea
          value={draft.question_text}
          onChange={(e) => set("question_text", e.target.value)}
          rows={4}
          className="input-field w-full resize-y leading-snug"
        />
      </label>

      {LETTERS.map((letter) => (
        <label key={letter} className="flex flex-col gap-1.5">
          <span className="text-[13px] font-medium text-[var(--muted)]">Choice {letter}</span>
          <textarea
            value={draft[choiceKey(letter)]}
            onChange={(e) => set(choiceKey(letter), e.target.value)}
            rows={2}
            className="input-field w-full resize-y leading-snug"
          />
        </label>
      ))}

      <div className="flex flex-col gap-1.5">
        <span className="text-[13px] font-medium text-[var(--muted)]">Correct answer</span>
        <div className="flex gap-2">
          {LETTERS.map((letter) => (
            <button
              key={letter}
              type="button"
              onClick={() => set("correct_answer", letter)}
              aria-pressed={draft.correct_answer === letter}
              className={`chip min-w-12 ${draft.correct_answer === letter ? "chip-selected" : ""}`}
            >
              {letter}
            </button>
          ))}
        </div>
      </div>

      <div className="flex flex-col gap-2 text-[14px]">
        <label className="flex items-center gap-2">
          <input type="checkbox" checked={draft.needs_review} onChange={(e) => set("needs_review", e.target.checked)} />
          Needs review
        </label>
        <label className="flex items-center gap-2">
          <input type="checkbox" checked={draft.is_active} onChange={(e) => set("is_active", e.target.checked)} />
          Active (shown in quizzes)
        </label>
      </div>

      {!complete && <p className="text-[13px] text-incorrect">The question and all four choices need text.</p>}
      {error && <p className="text-[13px] text-incorrect">{error}</p>}

      <div className="flex gap-3">
        <button type="submit" disabled={!dirty || !complete || saving} className="btn-primary">
          {saving ? "Saving…" : "Save changes"}
        </button>
        <button type="button" onClick={onCancel} className="btn-ghost">
          Cancel
        </button>
      </div>
    </form>
  );
}

export default function QuestionDrawer({
  question,
  mode,
  onModeChange,
  onClose,
  onSaved,
}: {
  question: AdminQuestion;
  mode: "view" | "edit";
  onModeChange: (mode: "view" | "edit") => void;
  onClose: () => void;
  onSaved: (question: AdminQuestion) => void;
}) {
  const dirty = useRef(false);

  // Leaving the form throws away unsaved edits, so ask first.
  function leaveForm(then: () => void) {
    if (mode === "edit" && dirty.current && !window.confirm("Discard your changes?")) return;
    dirty.current = false;
    then();
  }

  const requestClose = () => leaveForm(onClose);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") requestClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <div className="drawer-backdrop absolute inset-0" onClick={requestClose} />
      <aside
        role="dialog"
        aria-modal="true"
        aria-label={`${mode === "edit" ? "Edit" : "View"} question ${question.question_number}`}
        className="drawer-panel relative flex h-full w-full max-w-lg flex-col overflow-hidden sm:m-2 sm:h-[calc(100%-1rem)] sm:rounded-[var(--radius-card)]"
      >
        <div className="flex items-start justify-between gap-3 border-b border-[var(--hairline)] p-5">
          <div>
            <h2 className="text-[17px] font-semibold">
              {mode === "edit" ? "Edit question" : "Question"} #{question.question_number}
            </h2>
            <p className="text-[13px] text-[var(--muted)]">{question.source_file}</p>
          </div>
          <button
            type="button"
            onClick={requestClose}
            aria-label="Close"
            className="icon-button text-[22px] leading-none"
          >
            ×
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-5">
          {mode === "view" ? (
            <div className="flex flex-col gap-6">
              <QuestionView question={question} />
              <div className="flex gap-3">
                <button type="button" onClick={() => onModeChange("edit")} className="btn-primary">
                  Edit
                </button>
                <button type="button" onClick={onClose} className="btn-ghost">
                  Close
                </button>
              </div>
            </div>
          ) : (
            <QuestionForm
              key={question.id}
              question={question}
              onDirtyChange={(d) => {
                dirty.current = d;
              }}
              onSaved={(saved) => {
                dirty.current = false;
                onSaved(saved);
              }}
              onCancel={() => leaveForm(() => onModeChange("view"))}
            />
          )}
        </div>
      </aside>
    </div>
  );
}

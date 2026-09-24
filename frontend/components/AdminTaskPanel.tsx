"use client";

import { useEffect, useState } from "react";
import { createTask, fetchSourceFiles, fetchTasks, updateTask, type Task } from "@/lib/api";

export default function AdminTaskPanel() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [sourceFiles, setSourceFiles] = useState<string[]>([]);
  const [name, setName] = useState("");
  const [count, setCount] = useState(20);
  const [sourceFile, setSourceFile] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function load() {
    const [t, sf] = await Promise.all([fetchTasks(), fetchSourceFiles()]);
    setTasks(t);
    setSourceFiles(sf);
  }

  useEffect(() => {
    void load();
  }, []);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      await createTask({ name, question_count: count, source_file: sourceFile || null });
      setName("");
      setCount(20);
      setSourceFile("");
      await load();
    } catch (e) {
      setError(String(e));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleSourceFileChange(taskId: string, value: string) {
    setError("");
    try {
      await updateTask(taskId, { source_file: value || null });
      await load();
    } catch (e) {
      setError(String(e));
    }
  }

  async function handleCountChange(taskId: string, value: number) {
    if (!Number.isFinite(value) || value < 1) return;
    setError("");
    try {
      await updateTask(taskId, { question_count: value });
      await load();
    } catch (e) {
      setError(String(e));
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <form onSubmit={handleCreate} className="glass-card flex flex-wrap items-end gap-3 p-5">
        <label className="flex flex-1 flex-col gap-1.5 sm:flex-none">
          <span className="text-[13px] font-medium text-[var(--muted)]">Task name</span>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            className="input-field w-full sm:w-40"
          />
        </label>
        <label className="flex flex-1 flex-col gap-1.5 sm:flex-none">
          <span className="text-[13px] font-medium text-[var(--muted)]">Question count</span>
          <input
            type="number"
            min={1}
            value={count}
            onChange={(e) => setCount(Number(e.target.value))}
            className="input-field w-full sm:w-28"
          />
        </label>
        <label className="flex flex-1 flex-col gap-1.5 sm:flex-none">
          <span className="text-[13px] font-medium text-[var(--muted)]">Source file</span>
          <select
            value={sourceFile}
            onChange={(e) => setSourceFile(e.target.value)}
            className="input-field w-full sm:w-48"
          >
            <option value="">All files</option>
            {sourceFiles.map((sf) => (
              <option key={sf} value={sf}>
                {sf}
              </option>
            ))}
          </select>
        </label>
        <button type="submit" disabled={submitting || !name} className="btn-primary w-full sm:w-auto">
          Create task
        </button>
      </form>

      {error && <p className="text-[13px] text-incorrect">{error}</p>}

      {tasks.length === 0 ? (
        <p className="text-[13px] text-[var(--muted)]">No tasks yet.</p>
      ) : (
        <>
          {/* Mobile: stacked cards */}
          <div className="flex flex-col gap-3 sm:hidden">
            {tasks.map((t) => (
              <div key={t.id} className="glass-card flex flex-col gap-2 p-4">
                <span className="text-[14px] font-medium">{t.name}</span>
                <div className="flex gap-2">
                  <label className="flex flex-1 flex-col gap-1">
                    <span className="text-[12px] text-[var(--muted)]">Questions</span>
                    <input
                      type="number"
                      min={1}
                      defaultValue={t.question_count}
                      onBlur={(e) => handleCountChange(t.id, Number(e.target.value))}
                      className="input-field"
                    />
                  </label>
                  <label className="flex flex-1 flex-col gap-1">
                    <span className="text-[12px] text-[var(--muted)]">Source file</span>
                    <select
                      value={t.source_file ?? ""}
                      onChange={(e) => handleSourceFileChange(t.id, e.target.value)}
                      className="input-field"
                    >
                      <option value="">All files</option>
                      {sourceFiles.map((sf) => (
                        <option key={sf} value={sf}>
                          {sf}
                        </option>
                      ))}
                    </select>
                  </label>
                </div>
              </div>
            ))}
          </div>

          {/* Tablet/desktop: table */}
          <div className="glass-card hidden overflow-x-auto sm:block">
            <table className="data-table w-full text-[14px]">
              <thead>
                <tr className="text-left">
                  <th>Name</th>
                  <th>Questions</th>
                  <th>Source file</th>
                </tr>
              </thead>
              <tbody>
                {tasks.map((t) => (
                  <tr key={t.id}>
                    <td className="font-medium">{t.name}</td>
                    <td>
                      <input
                        type="number"
                        min={1}
                        defaultValue={t.question_count}
                        onBlur={(e) => handleCountChange(t.id, Number(e.target.value))}
                        className="input-field w-20"
                      />
                    </td>
                    <td>
                      <select
                        value={t.source_file ?? ""}
                        onChange={(e) => handleSourceFileChange(t.id, e.target.value)}
                        className="input-field"
                      >
                        <option value="">All files</option>
                        {sourceFiles.map((sf) => (
                          <option key={sf} value={sf}>
                            {sf}
                          </option>
                        ))}
                      </select>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}

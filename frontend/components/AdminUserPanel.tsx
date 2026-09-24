"use client";

import { useEffect, useState } from "react";
import { createUser, fetchUsers, updateUser, type AuthUser, type Role } from "@/lib/api";

export default function AdminUserPanel() {
  const [users, setUsers] = useState<AuthUser[]>([]);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<Role>("user");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function load() {
    setUsers(await fetchUsers());
  }

  useEffect(() => {
    fetchUsers()
      .then(setUsers)
      .catch((e) => setError(String(e)));
  }, []);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      await createUser({ name, username: email, password, role });
      setName("");
      setEmail("");
      setPassword("");
      setRole("user");
      await load();
    } catch (e) {
      setError(String(e));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleRoleChange(userId: string, newRole: Role) {
    setError("");
    try {
      await updateUser(userId, { role: newRole });
      await load();
    } catch (e) {
      setError(String(e));
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <form onSubmit={handleCreate} autoComplete="off" className="glass-card flex flex-wrap items-end gap-3 p-5">
        <label className="flex min-w-40 flex-1 flex-col gap-1.5">
          <span className="text-[13px] font-medium text-[var(--muted)]">Name</span>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            autoComplete="off"
            placeholder="Full name"
            className="input-field w-full"
          />
        </label>
        <label className="flex min-w-56 flex-[1.4] flex-col gap-1.5">
          <span className="text-[13px] font-medium text-[var(--muted)]">Email</span>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            inputMode="email"
            autoCapitalize="none"
            autoCorrect="off"
            spellCheck={false}
            autoComplete="off"
            placeholder="name@gmail.com"
            className="input-field w-full"
          />
        </label>
        <label className="flex min-w-40 flex-1 flex-col gap-1.5">
          <span className="text-[13px] font-medium text-[var(--muted)]">Password</span>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            autoComplete="new-password"
            className="input-field w-full"
          />
        </label>
        <label className="flex w-full flex-col gap-1.5 sm:w-28">
          <span className="text-[13px] font-medium text-[var(--muted)]">Role</span>
          <select value={role} onChange={(e) => setRole(e.target.value as Role)} className="input-field w-full">
            <option value="user">User</option>
            <option value="admin">Admin</option>
          </select>
        </label>
        <button
          type="submit"
          disabled={submitting || !name.trim() || !email.trim() || !password}
          className="btn-primary w-full sm:w-auto"
        >
          Create user
        </button>
      </form>

      {error && <p className="text-[13px] text-incorrect">{error}</p>}

      {users.length === 0 ? (
        <p className="text-[13px] text-[var(--muted)]">No users yet.</p>
      ) : (
        <>
          {/* Mobile: stacked cards */}
          <div className="flex flex-col gap-3 sm:hidden">
            {users.map((u) => (
              <div key={u.id} className="glass-card flex items-center justify-between gap-3 p-4">
                <div className="min-w-0">
                  <p className="truncate text-[14px] font-medium">{u.name || "—"}</p>
                  <p className="truncate text-[13px] text-[var(--muted)]">{u.username}</p>
                </div>
                <select
                  value={u.role}
                  onChange={(e) => handleRoleChange(u.id, e.target.value as Role)}
                  className="input-field"
                >
                  <option value="user">User</option>
                  <option value="admin">Admin</option>
                </select>
              </div>
            ))}
          </div>

          {/* Tablet/desktop: table */}
          <div className="glass-card hidden overflow-x-auto sm:block">
            <table className="data-table w-full text-[14px]">
              <thead>
                <tr className="text-left">
                  <th>Name</th>
                  <th>Email</th>
                  <th>Role</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id}>
                    <td className="font-medium">{u.name || <span className="text-[var(--muted)]">—</span>}</td>
                    <td className="text-[var(--muted)]">{u.username}</td>
                    <td>
                      <select
                        value={u.role}
                        onChange={(e) => handleRoleChange(u.id, e.target.value as Role)}
                        className="input-field"
                      >
                        <option value="user">User</option>
                        <option value="admin">Admin</option>
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

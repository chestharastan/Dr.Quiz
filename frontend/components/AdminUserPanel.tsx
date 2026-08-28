"use client";

import { useEffect, useState } from "react";
import { createUser, fetchUsers, updateUser, type AuthUser, type Role } from "@/lib/api";

export default function AdminUserPanel() {
  const [users, setUsers] = useState<AuthUser[]>([]);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<Role>("user");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function load() {
    setUsers(await fetchUsers());
  }

  useEffect(() => {
    void load();
  }, []);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      await createUser({ username, password, role });
      setUsername("");
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
      <form onSubmit={handleCreate} className="glass-card flex flex-wrap items-end gap-3 p-5">
        <label className="flex flex-1 flex-col gap-1.5 sm:flex-none">
          <span className="text-[13px] font-medium text-[var(--muted)]">Username</span>
          <input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
            className="input-field w-full sm:w-36"
          />
        </label>
        <label className="flex flex-1 flex-col gap-1.5 sm:flex-none">
          <span className="text-[13px] font-medium text-[var(--muted)]">Password</span>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            className="input-field w-full sm:w-36"
          />
        </label>
        <label className="flex flex-1 flex-col gap-1.5 sm:flex-none">
          <span className="text-[13px] font-medium text-[var(--muted)]">Role</span>
          <select
            value={role}
            onChange={(e) => setRole(e.target.value as Role)}
            className="input-field w-full sm:w-28"
          >
            <option value="user">User</option>
            <option value="admin">Admin</option>
          </select>
        </label>
        <button
          type="submit"
          disabled={submitting || !username || !password}
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
              <div key={u.id} className="glass-card flex items-center justify-between gap-2 p-4">
                <span className="text-[14px] font-medium">{u.username}</span>
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
          <div className="glass-card hidden overflow-x-auto p-2 sm:block">
            <table className="w-full border-collapse text-sm">
              <thead>
                <tr className="text-left text-[13px] text-[var(--muted)]">
                  <th className="p-3">Username</th>
                  <th className="p-3">Role</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id} className="border-t border-[var(--hairline)]">
                    <td className="p-3 font-medium">{u.username}</td>
                    <td className="p-3">
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

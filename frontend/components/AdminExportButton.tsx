"use client";

import { downloadExport } from "@/lib/api";

export default function AdminExportButton() {
  return (
    <div className="flex gap-2">
      <button onClick={() => downloadExport("json")} className="btn-ghost">
        Export JSON
      </button>
      <button onClick={() => downloadExport("csv")} className="btn-ghost">
        Export CSV
      </button>
    </div>
  );
}

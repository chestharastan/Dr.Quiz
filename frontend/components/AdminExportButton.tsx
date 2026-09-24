"use client";

import { downloadExport } from "@/lib/api";
import { DownloadIcon } from "@/components/icons";

export default function AdminExportButton() {
  return (
    <div className="flex gap-2">
      <button type="button" onClick={() => downloadExport("json")} className="btn-ghost btn-sm">
        <DownloadIcon />
        Export JSON
      </button>
      <button type="button" onClick={() => downloadExport("csv")} className="btn-ghost btn-sm">
        <DownloadIcon />
        Export CSV
      </button>
    </div>
  );
}

"use client";

import React, { useState } from "react";
import { Shield, Search, Terminal, Globe, Clock } from "lucide-react";
import { AuditLog } from "@/types";
import { formatDateTime } from "@/lib/utils";

interface AuditLogTableProps {
  logs: AuditLog[];
}

export function AuditLogTable({ logs }: AuditLogTableProps) {
  const [query, setQuery] = useState("");

  const filtered = logs.filter((log) => {
    if (!query.trim()) return true;
    const q = query.toLowerCase();
    return (
      log.action.toLowerCase().includes(q) ||
      log.target_entity.toLowerCase().includes(q) ||
      log.ip_address.toLowerCase().includes(q) ||
      JSON.stringify(log.details).toLowerCase().includes(q)
    );
  });

  return (
    <div className="rounded-xl bg-white border border-slate-200 shadow-2xs overflow-hidden">
      <div className="px-5 py-4 border-b border-slate-200 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <div className="h-8 w-8 rounded-lg bg-slate-900 text-white flex items-center justify-center">
            <Shield className="h-4 w-4" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-slate-900">
              Immutable System Audit Trail (PostgreSQL JSONB)
            </h3>
            <p className="text-xs text-slate-500">
              Indexed via <span className="font-mono">idx_audit_timestamp</span> • Zero-PII
              Scrubbed Records
            </p>
          </div>
        </div>

        <div className="relative w-full sm:w-72">
          <Search className="h-3.5 w-3.5 text-slate-400 absolute left-3 top-2.5" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Filter action, entity, IP..."
            className="w-full rounded-md border border-slate-300 pl-8 pr-3 py-1.5 text-xs text-slate-900 placeholder:text-slate-400 focus:border-brand-600 focus:outline-none"
          />
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-slate-200 bg-slate-50/80 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
              <th className="py-3 px-4">Timestamp</th>
              <th className="py-3 px-4">Action Event</th>
              <th className="py-3 px-4">Target Entity</th>
              <th className="py-3 px-4">Actor UUID &amp; IP</th>
              <th className="py-3 px-4">JSONB Metadata</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200 text-xs">
            {filtered.length === 0 ? (
              <tr>
                <td colSpan={5} className="py-8 text-center text-slate-500">
                  No matching audit trail entries found.
                </td>
              </tr>
            ) : (
              filtered.map((log) => (
                <tr key={log.log_id} className="hover:bg-slate-50/80 transition-colors">
                  <td className="py-3 px-4 font-mono text-[11px] text-slate-600 whitespace-nowrap">
                    <span className="inline-flex items-center gap-1">
                      <Clock className="h-3 w-3 text-slate-400" />
                      {formatDateTime(log.timestamp)}
                    </span>
                  </td>
                  <td className="py-3 px-4 whitespace-nowrap">
                    <span className="inline-flex items-center gap-1.5 font-mono text-[11px] font-semibold px-2 py-0.5 rounded bg-slate-100 text-slate-800 border border-slate-200">
                      <Terminal className="h-3 w-3 text-brand-600" />
                      {log.action}
                    </span>
                  </td>
                  <td className="py-3 px-4 font-mono text-[11px] text-slate-700 whitespace-nowrap">
                    {log.target_entity}
                  </td>
                  <td className="py-3 px-4 font-mono text-[11px] text-slate-600 whitespace-nowrap">
                    <div>{log.actor_id ? `${log.actor_id.slice(0, 8)}...` : "SYSTEM"}</div>
                    <div className="text-[10px] text-slate-400 inline-flex items-center gap-1">
                      <Globe className="h-2.5 w-2.5" />
                      {log.ip_address}
                    </div>
                  </td>
                  <td className="py-3 px-4">
                    <pre className="text-[11px] font-mono text-slate-600 bg-slate-50 border border-slate-200 rounded px-2.5 py-1.5 max-w-md overflow-x-auto">
                      {JSON.stringify(log.details)}
                    </pre>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
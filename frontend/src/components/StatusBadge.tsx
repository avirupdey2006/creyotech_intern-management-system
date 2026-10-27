import React from "react";
import { ApplicationStatus } from "@/types";
import { STATUS_META, cn } from "@/lib/utils";

interface StatusBadgeProps {
  status: ApplicationStatus;
  size?: "sm" | "md";
}

export function StatusBadge({ status, size = "md" }: StatusBadgeProps) {
  const meta = STATUS_META[status] || STATUS_META.SUBMITTED;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 font-medium border rounded-md whitespace-nowrap",
        size === "sm" ? "px-2 py-0.5 text-xs" : "px-2.5 py-1 text-xs",
        meta.badgeClass
      )}
    >
      <span className={cn("h-1.5 w-1.5 rounded-full", meta.dotClass)} />
      {meta.label}
    </span>
  );
}
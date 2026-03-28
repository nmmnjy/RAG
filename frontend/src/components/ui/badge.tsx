import * as React from "react";

import { cn } from "@/lib/utils";

type BadgeVariant = "default" | "warning" | "danger" | "success";

const badgeVariantClass: Record<BadgeVariant, string> = {
  default: "bg-[var(--surface-muted)] text-[#374032]",
  warning: "bg-[#fdecc8] text-[#6b4a0e]",
  danger: "bg-[#fce2e2] text-[#8a2525]",
  success: "bg-[#dff3e7] text-[#1e5a34]"
};

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant;
}

export function Badge({ className, variant = "default", ...props }: BadgeProps): React.JSX.Element {
  return (
    <span
      className={cn("inline-flex h-6 items-center rounded-md px-2 text-xs font-medium", badgeVariantClass[variant], className)}
      {...props}
    />
  );
}

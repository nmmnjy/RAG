import * as React from "react";

import { cn } from "@/lib/utils";

type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";

const buttonVariantClass: Record<ButtonVariant, string> = {
  primary: "bg-[var(--brand)] text-[var(--brand-foreground)] hover:opacity-90",
  secondary: "bg-[var(--surface-muted)] text-[var(--foreground)] border border-[var(--border)] hover:bg-[#e5eadf]",
  ghost: "bg-transparent text-[var(--foreground)] hover:bg-[var(--surface-muted)]",
  danger: "bg-[var(--danger)] text-white hover:opacity-90"
};

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
}

export function Button({ className, variant = "primary", type = "button", ...props }: ButtonProps): React.JSX.Element {
  return (
    <button
      type={type}
      className={cn(
        "inline-flex h-10 items-center justify-center rounded-lg px-4 text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-60",
        buttonVariantClass[variant],
        className
      )}
      {...props}
    />
  );
}

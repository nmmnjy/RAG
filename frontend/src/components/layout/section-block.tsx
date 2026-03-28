import * as React from "react";

import { cn } from "@/lib/utils";

interface SectionBlockProps extends React.HTMLAttributes<HTMLElement> {
  title: string;
  description?: string;
}

export function SectionBlock({ title, description, children, className, ...props }: SectionBlockProps): React.JSX.Element {
  return (
    <section className={cn("space-y-4", className)} {...props}>
      <header className="space-y-1">
        <h2 className="text-lg font-semibold">{title}</h2>
        {description ? <p className="text-sm text-[#4f5645]">{description}</p> : null}
      </header>
      {children}
    </section>
  );
}

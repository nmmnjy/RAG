import Link from "next/link";

const adminLinks = [
  { href: "/admin/kbs", label: "知识库" },
  { href: "/admin/documents", label: "文档管理" },
  { href: "/admin/tasks", label: "任务状态" },
  { href: "/admin/logs", label: "日志看板" }
];

export default function AdminLayout({ children }: { children: React.ReactNode }): React.JSX.Element {
  return (
    <div className="space-y-5">
      <nav className="grid gap-2 md:grid-cols-4">
        {adminLinks.map((link) => (
          <Link
            key={link.href}
            href={link.href}
            className="rounded-lg border border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-sm text-[#40513d] hover:bg-[var(--surface-muted)]"
          >
            {link.label}
          </Link>
        ))}
      </nav>
      {children}
    </div>
  );
}

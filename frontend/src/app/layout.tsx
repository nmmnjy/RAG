import type { Metadata } from "next";
import Link from "next/link";

import "./globals.css";

export const metadata: Metadata = {
  title: "企业知识库问答系统",
  description: "06 模块前端骨架：用户问答与管理后台"
};

const topLinks = [
  { href: "/qa", label: "用户问答" },
  { href: "/history", label: "问答历史" },
  { href: "/admin/kbs", label: "管理后台" }
];

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>): React.JSX.Element {
  return (
    <html lang="zh-CN">
      <body>
        <div className="mx-auto flex min-h-screen max-w-6xl flex-col px-6 py-6">
          <header className="mb-6 rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4 shadow-sm">
            <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
              <div>
                <p className="text-xs tracking-[0.2em] text-[#5f6657]">RAG FRONTEND V1</p>
                <h1 className="text-lg font-semibold">企业知识库智能问答系统</h1>
              </div>
              <nav className="flex flex-wrap gap-2">
                {topLinks.map((link) => (
                  <Link
                    key={link.href}
                    href={link.href}
                    className="rounded-md border border-[var(--border)] bg-[var(--surface-muted)] px-3 py-2 text-sm text-[#374032] hover:bg-[#e5eadf]"
                  >
                    {link.label}
                  </Link>
                ))}
              </nav>
            </div>
          </header>
          <main className="flex-1">{children}</main>
        </div>
      </body>
    </html>
  );
}

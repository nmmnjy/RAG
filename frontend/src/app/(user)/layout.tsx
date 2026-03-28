import Link from "next/link";

const userLinks = [
  { href: "/qa", label: "问答" },
  { href: "/history", label: "历史" }
];

export default function UserLayout({ children }: { children: React.ReactNode }): React.JSX.Element {
  return (
    <div className="space-y-5">
      <div className="flex gap-2">
        {userLinks.map((link) => (
          <Link key={link.href} href={link.href} className="rounded-md px-3 py-2 text-sm text-[#40513d] hover:bg-[var(--surface-muted)]">
            {link.label}
          </Link>
        ))}
      </div>
      {children}
    </div>
  );
}

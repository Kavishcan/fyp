"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const LINKS = [
  { href: "/", label: "Chat" },
  { href: "/dashboard", label: "Dashboard" },
];

export function NavBar() {
  const pathname = usePathname();

  return (
    <nav className="flex items-center gap-6 px-6 py-3 border-b shrink-0 bg-card">
      <span className="font-semibold tracking-tight">FedSafeRouter</span>
      <div className="flex items-center gap-1">
        {LINKS.map((link) => (
          <Link
            key={link.href}
            href={link.href}
            className={cn(
              "px-3 py-1.5 rounded-md text-sm transition-colors",
              pathname === link.href
                ? "bg-accent text-accent-foreground font-medium"
                : "text-muted-foreground hover:text-foreground hover:bg-muted",
            )}
          >
            {link.label}
          </Link>
        ))}
      </div>
    </nav>
  );
}

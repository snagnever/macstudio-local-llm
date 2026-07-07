"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { LayoutDashboard, List, FolderOpen, Tag } from "lucide-react";

const navItems = [
  {
    title: "Dashboard",
    href: "/",
    icon: LayoutDashboard,
  },
  {
    title: "All Tasks",
    href: "/tasks",
    icon: List,
  },
  {
    title: "Categories",
    href: "/categories",
    icon: FolderOpen,
  },
  {
    title: "Tags",
    href: "/tags",
    icon: Tag,
  },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <div className="w-64 border-r bg-background min-h-screen hidden md:block">
      <div className="p-6">
        <h1 className="text-2xl font-bold">Task Manager</h1>
      </div>
      <nav className="px-4 space-y-2">
        {navItems.map((item) => {
          const isActive = pathname === item.href || pathname.startsWith(`${item.href}/`);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 px-4 py-2 rounded-lg transition-colors",
                isActive ? "bg-primary text-primary-foreground" : "hover:bg-accent"
              )}
            >
              <item.icon className="h-5 w-5" />
              <span>{item.title}</span>
            </Link>
          );
        })}
      </nav>
    </div>
  );
}

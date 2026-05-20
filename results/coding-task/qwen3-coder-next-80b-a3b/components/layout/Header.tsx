"use client";

import { Button } from "@/components/ui/button";
import Link from "next/link";
import { Plus, Menu } from "lucide-react";

export function Header() {
  return (
    <header className="h-16 border-b px-4 flex items-center justify-between">
      <div className="flex items-center gap-4 md:hidden">
        <Button variant="ghost" size="icon">
          <Menu className="h-5 w-5" />
        </Button>
      </div>
      <div className="flex items-center gap-2 ml-auto">
        <Button asChild size="sm" className="hidden sm:flex">
          <Link href="/tasks/new">
            <Plus className="h-4 w-4 mr-2" />
            New Task
          </Link>
        </Button>
      </div>
    </header>
  );
}

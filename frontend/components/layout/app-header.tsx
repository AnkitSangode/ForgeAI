
"use client";

import {
  Search,
  Bell,
  Command,
  ChevronDown,
} from "lucide-react";
import { usePathname } from "next/navigation";

const pageTitles: Record<string, string> = {
  "/dashboard": "Dashboard",
  "/tasks": "Tasks",
  "/agents": "AI Agents",
  "/reviews": "Code Reviews",
  "/settings": "Settings",
};

export default function AppHeader() {
  const pathname = usePathname();

  const title =
    pageTitles[pathname] ||
    (pathname.startsWith("/tasks/") ? "Task Details" : "ForgeAI");

  return (
    <header className="sticky top-0 z-30 flex h-[72px] items-center justify-between border-b border-[#27272f] bg-[#09090b]/95 px-8 backdrop-blur-xl">

      <div>
        <h2 className="text-base font-semibold text-white">
          {title}
        </h2>

        <p className="mt-0.5 text-xs text-zinc-500">
          Your autonomous engineering workspace
        </p>
      </div>

      <div className="flex items-center gap-4">

        <button className="hidden h-9 items-center gap-3 rounded-lg border border-[#292932] bg-[#111114] px-3 text-xs text-zinc-500 sm:flex">
          <Search size={15} />
          Search anything...

          <span className="ml-5 flex items-center gap-1 rounded border border-[#33333d] px-1.5 py-0.5">
            <Command size={10} />
            K
          </span>
        </button>

        <button
          aria-label="Notifications"
          className="relative rounded-lg border border-[#292932] p-2.5 text-zinc-400 hover:bg-[#19191f]"
        >
          <Bell size={17} />

          <span className="absolute right-2 top-2 h-1.5 w-1.5 rounded-full bg-violet-400" />
        </button>

        <div className="hidden h-8 w-px bg-[#292932] sm:block" />

        <button
          aria-label="User profile"
          className="flex items-center gap-2"
        >
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-violet-500/20 text-xs font-semibold text-violet-300">
            AS
          </div>

          <ChevronDown
            size={15}
            className="text-zinc-500"
          />
        </button>

      </div>
    </header>
  );
}

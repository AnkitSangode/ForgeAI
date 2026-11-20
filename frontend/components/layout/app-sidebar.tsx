
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  ListTodo,
  Bot,
  GitPullRequest,
  Settings,
  Code2,
  Plus,
  Activity,
} from "lucide-react";

const navigation = [
  {
    title: "WORKSPACE",
    items: [
      {
        name: "Dashboard",
        href: "/dashboard",
        icon: LayoutDashboard,
      },
      {
        name: "Tasks",
        href: "/tasks",
        icon: ListTodo,
      },
      {
        name: "Agents",
        href: "/agents",
        icon: Bot,
      },
      {
        name: "Code Reviews",
        href: "/reviews",
        icon: GitPullRequest,
      },
    ],
  },
];

export default function AppSidebar() {
  const pathname = usePathname();

  return (
    <aside className="fixed left-0 top-0 z-40 flex h-screen w-[250px] flex-col border-r border-[#27272f] bg-[#0d0d10]">

      {/* Brand */}
      <div className="flex h-[72px] items-center border-b border-[#27272f] px-5">
        <Link
          href="/dashboard"
          className="flex items-center gap-3"
        >
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-violet-600">
            <Code2 size={21} />
          </div>

          <div>
            <h1 className="text-lg font-bold">
              Forge<span className="text-violet-400">AI</span>
            </h1>
            <p className="text-[10px] tracking-widest text-zinc-500">
              ENGINEERING PLATFORM
            </p>
          </div>
        </Link>
      </div>

      {/* Create task */}
      <div className="px-4 py-5">
        <Link
          href="/tasks/new"
          className="flex items-center justify-center gap-2 rounded-lg bg-violet-600 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-violet-500"
        >
          <Plus size={17} />
          New Task
        </Link>
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-7 px-3">
        {navigation.map((group) => (
          <div key={group.title}>
            <p className="mb-3 px-3 text-[10px] font-semibold tracking-[0.15em] text-zinc-600">
              {group.title}
            </p>

            <div className="space-y-1">
              {group.items.map((item) => {
                const Icon = item.icon;

                const active =
                  pathname === item.href ||
                  (item.href !== "/dashboard" &&
                    pathname.startsWith(item.href + "/"));

                return (
                  <Link
                    key={item.name}
                    href={item.href}
                    className={`sidebar-link ${
                      active ? "active" : ""
                    }`}
                  >
                    <Icon size={17} />
                    {item.name}
                  </Link>
                );
              })}
            </div>
          </div>
        ))}

        <div>
          <p className="mb-3 px-3 text-[10px] font-semibold tracking-[0.15em] text-zinc-600">
            SYSTEM
          </p>

          <Link
            href="/settings"
            className={`sidebar-link ${
              pathname.startsWith("/settings") ? "active" : ""
            }`}
          >
            <Settings size={17} />
            Settings
          </Link>

          <Link href="/dashboard" className="sidebar-link">
            <Activity size={17} />
            Activity
          </Link>
        </div>
      </nav>

      {/* User profile */}
      <div className="border-t border-[#27272f] p-4">
        <div className="flex items-center gap-3 rounded-lg p-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-violet-500/20 text-sm font-bold text-violet-300">
            AS
          </div>

          <div>
            <p className="text-sm font-medium text-white">
              Workspace Owner
            </p>
            <p className="text-xs text-zinc-500">
              Administrator
            </p>
          </div>
        </div>
      </div>
    </aside>
  );
}

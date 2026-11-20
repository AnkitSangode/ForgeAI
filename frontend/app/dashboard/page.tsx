
import Link from "next/link";
import DashboardLayout from "@/components/layout/dashboard-layout";
import {
  ArrowRight,
  ArrowUpRight,
  Bot,
  CheckCircle2,
  Clock3,
  GitBranch,
  ListTodo,
  Plus,
  Sparkles,
} from "lucide-react";

const stats = [
  {
    title: "Total Tasks",
    value: "24",
    description: "Tasks created",
    icon: ListTodo,
    color: "text-violet-400",
    bg: "bg-violet-500/10",
  },
  {
    title: "Completed",
    value: "18",
    description: "75% completion rate",
    icon: CheckCircle2,
    color: "text-emerald-400",
    bg: "bg-emerald-500/10",
  },
  {
    title: "In Progress",
    value: "03",
    description: "Currently executing",
    icon: Clock3,
    color: "text-blue-400",
    bg: "bg-blue-500/10",
  },
  {
    title: "Active Agents",
    value: "04",
    description: "Available agents",
    icon: Bot,
    color: "text-amber-400",
    bg: "bg-amber-500/10",
  },
];

const tasks = [
  {
    id: "TSK-024",
    title: "Implement JWT authentication",
    repo: "forgeai/backend",
    status: "In Progress",
    progress: 68,
    updated: "2 minutes ago",
  },
  {
    id: "TSK-023",
    title: "Create user management API",
    repo: "forgeai/api",
    status: "Completed",
    progress: 100,
    updated: "1 hour ago",
  },
  {
    id: "TSK-022",
    title: "Fix database connection pooling",
    repo: "forgeai/backend",
    status: "Review",
    progress: 90,
    updated: "3 hours ago",
  },
  {
    id: "TSK-021",
    title: "Implement error handling",
    repo: "forgeai/core",
    status: "Completed",
    progress: 100,
    updated: "Yesterday",
  },
];

const activities = [
  {
    title: "Code generation completed",
    description: "Authentication module generated.",
    time: "2 min ago",
    icon: CheckCircle2,
    color: "text-emerald-400",
  },
  {
    title: "Agent execution started",
    description: "Developer agent started TSK-024.",
    time: "8 min ago",
    icon: Bot,
    color: "text-violet-400",
  },
  {
    title: "New task created",
    description: "JWT authentication implementation.",
    time: "15 min ago",
    icon: Plus,
    color: "text-blue-400",
  },
];

const agents = [
  {
    name: "Planner Agent",
    role: "Task analysis and planning",
    status: "Ready",
  },
  {
    name: "Developer Agent",
    role: "Code generation",
    status: "Idle",
  },
  {
    name: "Reviewer Agent",
    role: "Code validation",
    status: "Ready",
  },
];

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    "In Progress": "bg-blue-500/10 text-blue-400",
    Completed: "bg-emerald-500/10 text-emerald-400",
    Review: "bg-amber-500/10 text-amber-400",
  };

  return (
    <span
      className={`rounded-md px-2.5 py-1 text-[11px] font-medium ${
        styles[status] || "bg-zinc-500/10 text-zinc-400"
      }`}
    >
      {status}
    </span>
  );
}

export default function DashboardPage() {
  return (
    <DashboardLayout>

      {/* Welcome */}
      <section className="mb-8 flex flex-col justify-between gap-5 sm:flex-row sm:items-center">
        <div>
          <div className="mb-2 flex items-center gap-2">
            <Sparkles size={16} className="text-violet-400" />
            <span className="text-xs font-medium tracking-wide text-violet-300">
              AUTONOMOUS ENGINEERING
            </span>
          </div>

          <h1 className="text-2xl font-bold tracking-tight text-white">
            Engineering Overview
          </h1>

          <p className="mt-2 text-sm text-zinc-500">
            Manage tasks, monitor AI agents and track engineering progress.
          </p>
        </div>

        <Link
          href="/tasks/new"
          className="flex items-center justify-center gap-2 rounded-lg bg-violet-600 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-violet-500"
        >
          <Plus size={16} />
          Create New Task
        </Link>
      </section>

      {/* Statistics */}
      <section className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {stats.map((stat) => {
          const Icon = stat.icon;

          return (
            <div key={stat.title} className="dashboard-card p-5">
              <div className="flex items-center justify-between">
                <p className="text-sm text-zinc-400">
                  {stat.title}
                </p>

                <div className={`rounded-lg p-2 ${stat.bg}`}>
                  <Icon size={18} className={stat.color} />
                </div>
              </div>

              <h2 className="mt-4 text-3xl font-bold text-white">
                {stat.value}
              </h2>

              <p className="mt-2 text-xs text-zinc-500">
                {stat.description}
              </p>
            </div>
          );
        })}
      </section>

      {/* Tasks and activity */}
      <section className="grid grid-cols-1 gap-5 xl:grid-cols-3">

        {/* Recent Tasks */}
        <div className="dashboard-card overflow-hidden xl:col-span-2">

          <div className="flex items-center justify-between border-b border-[#27272f] p-5">
            <div>
              <h3 className="text-sm font-semibold text-white">
                Recent Tasks
              </h3>

              <p className="mt-1 text-xs text-zinc-500">
                Latest engineering tasks
              </p>
            </div>

            <Link
              href="/tasks"
              className="flex items-center gap-1 text-xs text-violet-400 hover:text-violet-300"
            >
              View all
              <ArrowRight size={14} />
            </Link>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full min-w-[600px] text-left">
              <thead className="border-b border-[#27272f] bg-[#151519]">
                <tr className="text-[10px] tracking-wider text-zinc-500">
                  <th className="px-5 py-3">TASK</th>
                  <th className="px-5 py-3">STATUS</th>
                  <th className="px-5 py-3">PROGRESS</th>
                  <th className="px-5 py-3">UPDATED</th>
                </tr>
              </thead>

              <tbody>
                {tasks.map((task) => (
                  <tr
                    key={task.id}
                    className="border-b border-[#27272f] last:border-0 hover:bg-[#151519]"
                  >
                    <td className="px-5 py-4">
                      <p className="text-sm font-medium text-zinc-200">
                        {task.title}
                      </p>

                      <div className="mt-1 flex items-center gap-1.5 text-[11px] text-zinc-500">
                        <GitBranch size={12} />
                        {task.repo}
                        <span>· {task.id}</span>
                      </div>
                    </td>

                    <td className="px-5 py-4">
                      <StatusBadge status={task.status} />
                    </td>

                    <td className="px-5 py-4">
                      <div className="flex items-center gap-2">
                        <div className="h-1.5 w-16 overflow-hidden rounded-full bg-zinc-800">
                          <div
                            className="h-full rounded-full bg-violet-500"
                            style={{ width: `${task.progress}%` }}
                          />
                        </div>

                        <span className="text-xs text-zinc-400">
                          {task.progress}%
                        </span>
                      </div>
                    </td>

                    <td className="whitespace-nowrap px-5 py-4 text-xs text-zinc-500">
                      {task.updated}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Activity Feed */}
        <div className="dashboard-card">
          <div className="border-b border-[#27272f] p-5">
            <h3 className="text-sm font-semibold text-white">
              Recent Activity
            </h3>

            <p className="mt-1 text-xs text-zinc-500">
              Latest platform events
            </p>
          </div>

          <div className="space-y-6 p-5">
            {activities.map((activity) => {
              const Icon = activity.icon;

              return (
                <div key={activity.title} className="flex gap-3">
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-[#1c1c23]">
                    <Icon size={16} className={activity.color} />
                  </div>

                  <div>
                    <p className="text-xs font-medium text-zinc-200">
                      {activity.title}
                    </p>

                    <p className="mt-1 text-[11px] leading-5 text-zinc-500">
                      {activity.description}
                    </p>

                    <p className="mt-2 text-[10px] text-zinc-600">
                      {activity.time}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>

          <div className="border-t border-[#27272f] p-4">
            <Link
              href="/tasks"
              className="flex items-center justify-center gap-2 text-xs text-zinc-400 hover:text-white"
            >
              View task history
              <ArrowUpRight size={14} />
            </Link>
          </div>
        </div>
      </section>

      {/* Agent Infrastructure */}
      <section className="dashboard-card mt-5 p-5">
        <div className="mb-5 flex items-center justify-between">
          <div>
            <div className="flex items-center gap-2">
              <Bot size={17} className="text-violet-400" />

              <h3 className="text-sm font-semibold text-white">
                Agent Infrastructure
              </h3>
            </div>

            <p className="mt-1 text-xs text-zinc-500">
              Your autonomous engineering agents
            </p>
          </div>

          <span className="flex items-center gap-2 text-xs text-emerald-400">
            <span className="h-2 w-2 rounded-full bg-emerald-400" />
            System Ready
          </span>
        </div>

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          {agents.map((agent) => (
            <div
              key={agent.name}
              className="flex items-center justify-between rounded-lg border border-[#292932] bg-[#151519] p-4"
            >
              <div className="flex items-center gap-3">
                <div className="rounded-lg bg-violet-500/10 p-2">
                  <Bot size={17} className="text-violet-400" />
                </div>

                <div>
                  <p className="text-xs font-medium text-zinc-200">
                    {agent.name}
                  </p>

                  <p className="mt-1 text-[10px] text-zinc-500">
                    {agent.role}
                  </p>
                </div>
              </div>

              <span className="text-[10px] text-emerald-400">
                {agent.status}
              </span>
            </div>
          ))}
        </div>
      </section>

    </DashboardLayout>
  );
}

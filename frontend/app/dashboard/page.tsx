"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import DashboardLayout from "@/components/layout/dashboard-layout";
import { Activity, ArrowRight, Bot, CheckCircle2, Clock3, GitBranch, ListTodo, Loader2, Plus } from "lucide-react";
import { api, type Task } from "@/lib/api";

export default function DashboardPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    api.listTasks()
      .then(setTasks)
      .catch((err) => setError(err instanceof Error ? err.message : "Unable to load dashboard data."))
      .finally(() => setLoading(false));
  }, []);

  const completed = tasks.filter((task) => ["completed", "succeeded", "success"].includes(task.status.toLowerCase())).length;
  const active = tasks.filter((task) => ["running", "pending", "in_progress"].includes(task.status.toLowerCase())).length;
  const stats = [
    { label: "Total Tasks", value: tasks.length, icon: ListTodo },
    { label: "Completed", value: completed, icon: CheckCircle2 },
    { label: "In Progress", value: active, icon: Clock3 },
    { label: "Available Agents", value: 4, icon: Bot },
  ];

  return (
    <DashboardLayout>
      <div className="space-y-8">
        <section className="flex flex-col justify-between gap-5 sm:flex-row sm:items-center">
          <div>
            <div className="mb-2 flex items-center gap-2 text-xs font-medium tracking-wide text-violet-300"><Activity size={15}/>AUTONOMOUS ENGINEERING</div>
            <h1 className="text-2xl font-bold tracking-tight text-white">Engineering Overview</h1>
            <p className="mt-2 text-sm text-zinc-500">Your tasks and agent execution workspace.</p>
          </div>
          <Link href="/tasks/new" className="flex items-center justify-center gap-2 rounded-lg bg-violet-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-violet-500"><Plus size={16}/>Create New Task</Link>
        </section>

        {error && <div role="alert" className="rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-400">{error}</div>}

        <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {stats.map((stat) => {
            const Icon = stat.icon;
            return <div key={stat.label} className="dashboard-card p-5"><div className="flex items-center justify-between"><p className="text-sm text-zinc-400">{stat.label}</p><div className="rounded-lg bg-violet-500/10 p-2"><Icon size={18} className="text-violet-400"/></div></div><h2 className="mt-4 text-3xl font-bold text-white">{loading ? "—" : stat.value}</h2><p className="mt-2 text-xs text-zinc-500">Live data from ForgeAI API</p></div>;
          })}
        </section>

        <section className="dashboard-card overflow-hidden">
          <div className="flex items-center justify-between border-b border-[#27272f] p-5"><div><h2 className="text-sm font-semibold text-white">Recent Tasks</h2><p className="mt-1 text-xs text-zinc-500">Latest tasks stored by the backend</p></div><Link href="/tasks" className="flex items-center gap-1 text-xs text-violet-400">View all<ArrowRight size={14}/></Link></div>
          {loading ? <div className="flex justify-center p-14"><Loader2 className="animate-spin text-violet-400"/></div> : tasks.length ? <div className="divide-y divide-[#27272f]">{tasks.slice(0,6).map((task) => <div key={task.id} className="flex flex-col justify-between gap-3 p-5 sm:flex-row sm:items-center"><div className="min-w-0"><Link href={`/tasks/${task.id}`} className="font-medium text-white hover:text-violet-400">{task.title}</Link><p className="mt-2 flex items-center gap-2 break-all text-xs text-zinc-500"><GitBranch size={13}/>{task.repository_url}</p></div><span className="h-fit w-fit rounded-md bg-violet-500/10 px-3 py-1.5 text-xs capitalize text-violet-300">{task.status}</span></div>)}</div> : <div className="p-14 text-center"><ListTodo className="mx-auto mb-3 text-zinc-500"/><p className="text-sm text-zinc-300">No tasks yet.</p><Link href="/tasks/new" className="mt-4 inline-flex items-center gap-2 text-sm text-violet-400"><Plus size={15}/>Create your first task</Link></div>}
        </section>
      </div>
    </DashboardLayout>
  );
}

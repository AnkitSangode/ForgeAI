"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import DashboardLayout from "@/components/layout/dashboard-layout";
import { Plus, ListTodo, GitBranch, Clock3, ClipboardList, Loader2 } from "lucide-react";
import { api, type Task } from "@/lib/api";

export default function TasksPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    api.listTasks()
      .then(setTasks)
      .catch((err) => setError(err instanceof Error ? err.message : "Unable to load tasks."))
      .finally(() => setLoading(false));
  }, []);

  const active = tasks.filter((task) => ["running", "pending", "in_progress"].includes(task.status.toLowerCase())).length;
  const completed = tasks.filter((task) => ["completed", "succeeded", "success"].includes(task.status.toLowerCase())).length;

  return (
    <DashboardLayout>
      <div className="space-y-7">
        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
          <div>
            <h1 className="text-2xl font-bold text-white">Engineering Tasks</h1>
            <p className="mt-2 text-sm text-zinc-500">Manage and monitor your software engineering tasks.</p>
          </div>
          <Link href="/tasks/new" className="flex items-center justify-center gap-2 rounded-lg bg-violet-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-violet-500">
            <Plus size={17} /> Create Task
          </Link>
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <div className="dashboard-card p-5"><p className="text-sm text-zinc-400">Total Tasks</p><h2 className="mt-3 text-3xl font-bold text-white">{tasks.length}</h2></div>
          <div className="dashboard-card p-5"><p className="text-sm text-zinc-400">In Progress</p><h2 className="mt-3 text-3xl font-bold text-white">{active}</h2></div>
          <div className="dashboard-card p-5"><p className="text-sm text-zinc-400">Completed</p><h2 className="mt-3 text-3xl font-bold text-white">{completed}</h2></div>
        </div>

        <section className="dashboard-card overflow-hidden">
          <div className="flex items-center justify-between border-b border-[#27272f] p-5">
            <div><h2 className="text-sm font-semibold text-white">All Tasks</h2><p className="mt-1 text-xs text-zinc-500">Tasks stored by the ForgeAI backend</p></div>
            <ListTodo size={19} className="text-zinc-500" />
          </div>
          {loading ? (
            <div className="flex justify-center p-16"><Loader2 className="animate-spin text-violet-400" /></div>
          ) : error ? (
            <div role="alert" className="p-6 text-sm text-red-400">{error}</div>
          ) : tasks.length ? (
            <div className="divide-y divide-[#27272f]">
              {tasks.map((task) => (
                <div key={task.id} className="flex flex-col justify-between gap-4 p-5 sm:flex-row">
                  <div className="min-w-0">
                    <Link href={`/tasks/${task.id}`} className="font-semibold text-white hover:text-violet-400">{task.title}</Link>
                    <p className="mt-2 line-clamp-2 max-w-3xl text-sm text-zinc-400">{task.description}</p>
                    <div className="mt-3 flex flex-wrap gap-4 text-xs text-zinc-500">
                      <span className="flex items-center gap-2"><GitBranch size={13} />{task.repository_url}</span>
                      <span className="flex items-center gap-2"><Clock3 size={13} />{new Date(task.created_at).toLocaleString()}</span>
                    </div>
                  </div>
                  <span className="h-fit rounded-md bg-violet-500/10 px-3 py-1.5 text-xs capitalize text-violet-300">{task.status}</span>
                </div>
              ))}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center px-5 py-20 text-center">
              <ClipboardList size={30} className="mb-4 text-violet-400" />
              <h3 className="text-base font-semibold text-white">No tasks yet</h3>
              <p className="mt-2 text-sm text-zinc-500">Create your first engineering task to get started.</p>
              <Link href="/tasks/new" className="mt-5 flex items-center gap-2 rounded-lg bg-violet-600 px-4 py-2.5 text-sm text-white"><Plus size={16} />Create Your First Task</Link>
            </div>
          )}
        </section>
      </div>
    </DashboardLayout>
  );
}

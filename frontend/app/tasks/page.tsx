
"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import DashboardLayout from "@/components/layout/dashboard-layout";
import {
  Plus,
  ListTodo,
  GitBranch,
  Clock3,
  ArrowRight,
  ClipboardList,
} from "lucide-react";

type Task = {
  title: string;
  description: string;
  repositoryUrl: string;
  branch: string;
  priority: string;
  taskType: string;
};

export default function TasksPage() {
  const [task, setTask] = useState<Task | null>(null);

  useEffect(() => {
    const saved = sessionStorage.getItem("forgeai_pending_task");

    if (saved) {
      try {
        setTask(JSON.parse(saved) as Task);
      } catch {
        sessionStorage.removeItem("forgeai_pending_task");
      }
    }
  }, []);

  return (
    <DashboardLayout>
      <div className="space-y-7">

        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
          <div>
            <h1 className="text-2xl font-bold text-white">
              Engineering Tasks
            </h1>
            <p className="mt-2 text-sm text-zinc-500">
              Manage and monitor your software engineering tasks.
            </p>
          </div>

          <Link
            href="/tasks/new"
            className="flex items-center justify-center gap-2 rounded-lg bg-violet-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-violet-500"
          >
            <Plus size={17} />
            Create Task
          </Link>
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <div className="dashboard-card p-5">
            <p className="text-sm text-zinc-400">Total Tasks</p>
            <h2 className="mt-3 text-3xl font-bold text-white">
              {task ? "1" : "0"}
            </h2>
          </div>

          <div className="dashboard-card p-5">
            <p className="text-sm text-zinc-400">In Progress</p>
            <h2 className="mt-3 text-3xl font-bold text-white">0</h2>
          </div>

          <div className="dashboard-card p-5">
            <p className="text-sm text-zinc-400">Completed</p>
            <h2 className="mt-3 text-3xl font-bold text-white">0</h2>
          </div>
        </div>

        <section className="dashboard-card overflow-hidden">
          <div className="flex items-center justify-between border-b border-[#27272f] p-5">
            <div>
              <h2 className="text-sm font-semibold text-white">
                All Tasks
              </h2>
              <p className="mt-1 text-xs text-zinc-500">
                Your submitted engineering tasks
              </p>
            </div>

            <ListTodo size={19} className="text-zinc-500" />
          </div>

          {task ? (
            <div className="p-5">
              <div className="flex flex-col justify-between gap-4 sm:flex-row">
                <div>
                  <div className="mb-3 flex items-center gap-2">
                    <span className="rounded-md bg-violet-500/10 px-2 py-1 text-[10px] text-violet-400">
                      LOCAL DRAFT
                    </span>

                    <span className="text-xs text-zinc-600">
                      Not submitted to backend
                    </span>
                  </div>

                    <Link
                    href="/tasks/local-draft"
                    className="text-base font-semibold text-white hover:text-violet-400"
                    >
                    {task.title}
                    </Link>

                  <p className="mt-2 max-w-2xl text-sm leading-6 text-zinc-400">
                    {task.description}
                  </p>

                  <div className="mt-4 flex flex-wrap gap-4 text-xs text-zinc-500">
                    <span className="flex items-center gap-2">
                      <GitBranch size={14} />
                      {task.branch}
                    </span>

                    <span className="flex items-center gap-2">
                      <Clock3 size={14} />
                      {task.priority} priority
                    </span>
                  </div>

                  <a
                    href={task.repositoryUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="mt-4 inline-flex items-center gap-2 text-xs text-violet-400 hover:text-violet-300"
                  >
                    View GitHub Repository
                    <ArrowRight size={13} />
                  </a>
                </div>

                <div className="flex items-start">
                  <span className="rounded-md bg-zinc-500/10 px-3 py-1.5 text-xs text-zinc-400">
                    Awaiting backend submission
                  </span>
                </div>
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center px-5 py-20 text-center">
              <div className="mb-4 rounded-2xl bg-violet-500/10 p-4">
                <ClipboardList
                  size={30}
                  className="text-violet-400"
                />
              </div>

              <h3 className="text-base font-semibold text-white">
                No tasks yet
              </h3>

              <p className="mt-2 max-w-sm text-sm leading-6 text-zinc-500">
                You haven't prepared any engineering tasks yet.
                Create your first task to get started.
              </p>

              <Link
                href="/tasks/new"
                className="mt-5 flex items-center gap-2 rounded-lg bg-violet-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-violet-500"
              >
                <Plus size={16} />
                Create Your First Task
              </Link>
            </div>
          )}
        </section>
      </div>
    </DashboardLayout>
  );
}

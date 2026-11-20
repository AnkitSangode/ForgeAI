
"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import DashboardLayout from "@/components/layout/dashboard-layout";
import {
  ArrowLeft,
  Bot,
  CheckCircle2,
  Clock3,
  Code2,
  GitBranch,
  GitPullRequest,
  Loader2,
  Play,
  Terminal,
  CircleDot,
  FileCode2,
} from "lucide-react";

type Task = {
  title: string;
  description: string;
  repositoryUrl: string;
  branch: string;
  priority: string;
  taskType: string;
};

const workflow = [
  {
    name: "Task Analysis",
    description: "Analyze requirements and understand the codebase",
    status: "pending",
    icon: CircleDot,
  },
  {
    name: "Planning",
    description: "Create an implementation plan",
    status: "pending",
    icon: Bot,
  },
  {
    name: "Development",
    description: "Implement the requested changes",
    status: "pending",
    icon: Code2,
  },
  {
    name: "Code Review",
    description: "Validate generated code and changes",
    status: "pending",
    icon: GitPullRequest,
  },
];

export default function TaskDetailsPage() {
  const params = useParams<{ taskId: string }>();

  const [task, setTask] = useState<Task | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const saved = sessionStorage.getItem("forgeai_pending_task");

    if (saved) {
      try {
        setTask(JSON.parse(saved) as Task);
      } catch {
        setTask(null);
      }
    }

    setLoading(false);
  }, []);

  if (loading) {
    return (
      <DashboardLayout>
        <div className="flex min-h-[400px] items-center justify-center">
          <Loader2 className="animate-spin text-violet-400" />
        </div>
      </DashboardLayout>
    );
  }

  if (!task) {
    return (
      <DashboardLayout>
        <div className="dashboard-card flex flex-col items-center p-12 text-center">
          <FileCode2 size={36} className="mb-4 text-zinc-500" />
          <h2 className="text-lg font-semibold text-white">
            Task not found
          </h2>
          <p className="mt-2 text-sm text-zinc-500">
            This task is not available in the current browser session.
          </p>
          <Link
            href="/tasks"
            className="mt-5 text-sm text-violet-400"
          >
            Back to Tasks
          </Link>
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div className="space-y-6">

        <Link
          href="/tasks"
          className="inline-flex items-center gap-2 text-sm text-zinc-500 hover:text-white"
        >
          <ArrowLeft size={15} />
          Back to Tasks
        </Link>

        {/* Task heading */}
        <section className="flex flex-col justify-between gap-5 sm:flex-row sm:items-start">
          <div>
            <div className="mb-3 flex items-center gap-2">
              <span className="rounded-md bg-violet-500/10 px-2.5 py-1 text-[11px] text-violet-400">
                LOCAL DRAFT
              </span>
              <span className="text-xs text-zinc-500">
                {params.taskId}
              </span>
            </div>

            <h1 className="text-2xl font-bold text-white">
              {task.title}
            </h1>

            <p className="mt-2 max-w-2xl text-sm leading-6 text-zinc-500">
              {task.description}
            </p>
          </div>

          <button
            disabled
            title="Backend execution is not connected yet"
            className="flex cursor-not-allowed items-center justify-center gap-2 rounded-lg bg-violet-600/40 px-5 py-3 text-sm font-medium text-white/60"
          >
            <Play size={16} />
            Start Execution
          </button>
        </section>

        {/* Metadata */}
        <section className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <div className="dashboard-card p-5">
            <div className="flex items-center gap-2 text-xs text-zinc-500">
              <GitBranch size={15} />
              Repository Branch
            </div>
            <p className="mt-3 text-sm font-medium text-white">
              {task.branch}
            </p>
          </div>

          <div className="dashboard-card p-5">
            <div className="flex items-center gap-2 text-xs text-zinc-500">
              <CircleDot size={15} />
              Priority
            </div>
            <p className="mt-3 text-sm font-medium capitalize text-white">
              {task.priority}
            </p>
          </div>

          <div className="dashboard-card p-5">
            <div className="flex items-center gap-2 text-xs text-zinc-500">
              <Code2 size={15} />
              Task Type
            </div>
            <p className="mt-3 text-sm font-medium capitalize text-white">
              {task.taskType}
            </p>
          </div>
        </section>

        <div className="grid grid-cols-1 gap-5 xl:grid-cols-3">

          {/* Workflow */}
          <section className="dashboard-card p-5 xl:col-span-2">
            <div className="mb-6">
              <h2 className="text-sm font-semibold text-white">
                Agent Execution Workflow
              </h2>
              <p className="mt-1 text-xs text-zinc-500">
                Planned stages of autonomous task execution
              </p>
            </div>

            <div className="space-y-6">
              {workflow.map((step, index) => {
                const Icon = step.icon;

                return (
                  <div key={step.name} className="flex gap-4">
                    <div className="flex flex-col items-center">
                      <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-[#30303a] bg-[#19191f]">
                        <Icon size={18} className="text-zinc-400" />
                      </div>

                      {index !== workflow.length - 1 && (
                        <div className="mt-2 h-7 w-px bg-[#30303a]" />
                      )}
                    </div>

                    <div className="flex-1 pb-3">
                      <div className="flex items-center justify-between gap-3">
                        <h3 className="text-sm font-medium text-zinc-200">
                          {step.name}
                        </h3>

                        <span className="rounded-md bg-zinc-500/10 px-2 py-1 text-[10px] text-zinc-500">
                          Pending
                        </span>
                      </div>

                      <p className="mt-1 text-xs text-zinc-500">
                        {step.description}
                      </p>
                    </div>
                  </div>
                );
              })}
            </div>
          </section>

          {/* Execution status */}
          <section className="dashboard-card h-fit p-5">
            <h2 className="text-sm font-semibold text-white">
              Execution Status
            </h2>

            <div className="mt-6 flex flex-col items-center rounded-xl border border-[#30303a] bg-[#151519] p-6 text-center">
              <div className="rounded-full bg-amber-500/10 p-4">
                <Clock3 size={25} className="text-amber-400" />
              </div>

              <h3 className="mt-4 text-sm font-semibold text-white">
                Awaiting Execution
              </h3>

              <p className="mt-2 text-xs leading-5 text-zinc-500">
                This task has been prepared locally. Backend execution
                has not started.
              </p>
            </div>

            <div className="mt-5 space-y-4">
              <div className="flex justify-between text-xs">
                <span className="text-zinc-500">Progress</span>
                <span className="text-white">0%</span>
              </div>

              <div className="h-1.5 overflow-hidden rounded-full bg-zinc-800">
                <div className="h-full w-0 bg-violet-500" />
              </div>

              <div className="flex justify-between text-xs">
                <span className="text-zinc-500">Agents started</span>
                <span className="text-white">0 / 4</span>
              </div>
            </div>
          </section>
        </div>

        {/* Repository */}
        <section className="dashboard-card p-5">
          <div className="flex items-center gap-3">
            <Code2 size={19} className="text-violet-400" />
            <h2 className="text-sm font-semibold text-white">
              Connected Repository
            </h2>
          </div>

          <a
            href={task.repositoryUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="mt-4 block break-all text-sm text-violet-400 hover:text-violet-300"
          >
            {task.repositoryUrl}
          </a>

          <p className="mt-2 text-xs text-zinc-500">
            Target branch: {task.branch}
          </p>
        </section>

        {/* Execution logs */}
        <section className="dashboard-card overflow-hidden">
          <div className="flex items-center gap-3 border-b border-[#27272f] p-5">
            <Terminal size={18} className="text-violet-400" />
            <div>
              <h2 className="text-sm font-semibold text-white">
                Execution Logs
              </h2>
              <p className="mt-1 text-xs text-zinc-500">
                Agent events and execution output
              </p>
            </div>
          </div>

          <div className="bg-[#0b0b0e] p-5 font-mono text-xs">
            <p className="text-zinc-500">
              [SYSTEM] Task configuration loaded.
            </p>
            <p className="mt-3 text-zinc-500">
              [SYSTEM] Repository URL configured.
            </p>
            <p className="mt-3 text-amber-400">
              [WAITING] Backend execution service not connected.
            </p>
          </div>
        </section>

      </div>
    </DashboardLayout>
  );
}

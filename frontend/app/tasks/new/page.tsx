
"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import DashboardLayout from "@/components/layout/dashboard-layout";
import {
  ArrowLeft,
  ArrowRight,
  Bot,
  CheckCircle2,
  Code2,
  GitBranch,
  Info,
  Loader2,
  Sparkles,
} from "lucide-react";

export default function CreateTaskPage() {
  const router = useRouter();

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [repositoryUrl, setRepositoryUrl] = useState("");
  const [branch, setBranch] = useState("main");
  const [priority, setPriority] = useState("medium");
  const [taskType, setTaskType] = useState("feature");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");

    if (!title.trim() || !description.trim() || !repositoryUrl.trim()) {
      setError("Please complete all required fields.");
      return;
    }

    try {
      const url = new URL(repositoryUrl);

      if (
        url.hostname !== "github.com" &&
        url.hostname !== "www.github.com"
      ) {
        setError("Please enter a valid GitHub repository URL.");
        return;
      }

      if (url.pathname.split("/").filter(Boolean).length < 2) {
        setError("Please enter a GitHub owner and repository name.");
        return;
      }
    } catch {
      setError("Please enter a valid repository URL.");
      return;
    }

    // Temporary frontend submission.
    // Replace this with the backend API call during integration.
    setSubmitting(true);

    const task = {
      title: title.trim(),
      description: description.trim(),
      repositoryUrl: repositoryUrl.trim(),
      branch: branch.trim(),
      priority,
      taskType,
    };

    sessionStorage.setItem(
      "forgeai_pending_task",
      JSON.stringify(task)
    );

    router.push("/tasks");
  }

  return (
    <DashboardLayout>
      <div className="mx-auto max-w-4xl">

        {/* Breadcrumb */}
        <Link
          href="/dashboard"
          className="mb-6 inline-flex items-center gap-2 text-sm text-zinc-500 hover:text-white"
        >
          <ArrowLeft size={15} />
          Back to Dashboard
        </Link>

        {/* Heading */}
        <div className="mb-8">
          <div className="mb-3 flex items-center gap-2">
            <div className="rounded-lg bg-violet-500/10 p-2">
              <Sparkles size={18} className="text-violet-400" />
            </div>

            <span className="text-xs font-medium tracking-wider text-violet-400">
              AUTONOMOUS ENGINEERING
            </span>
          </div>

          <h1 className="text-2xl font-bold text-white">
            Create New Task
          </h1>

          <p className="mt-2 text-sm text-zinc-500">
            Describe what you want ForgeAI to build, fix or improve.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">

          {/* Task information */}
          <section className="dashboard-card p-6">
            <div className="mb-6 flex items-center gap-3">
              <div className="rounded-lg bg-violet-500/10 p-2">
                <Code2 size={18} className="text-violet-400" />
              </div>

              <div>
                <h2 className="text-sm font-semibold text-white">
                  Task Information
                </h2>
                <p className="mt-1 text-xs text-zinc-500">
                  Define the engineering work you want done.
                </p>
              </div>
            </div>

            <div className="space-y-5">

              <div>
                <label className="mb-2 block text-sm font-medium text-zinc-300">
                  Task Title <span className="text-red-400">*</span>
                </label>

                <input
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="e.g. Implement JWT authentication"
                  maxLength={150}
                  required
                  className="w-full rounded-lg border border-[#30303a] bg-[#151519] px-4 py-3 text-sm text-white outline-none transition placeholder:text-zinc-600 focus:border-violet-500"
                />
              </div>

              <div>
                <label className="mb-2 block text-sm font-medium text-zinc-300">
                  Task Description <span className="text-red-400">*</span>
                </label>

                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Describe the problem, expected behavior, technical requirements and acceptance criteria..."
                  rows={7}
                  maxLength={10000}
                  required
                  className="w-full resize-y rounded-lg border border-[#30303a] bg-[#151519] px-4 py-3 text-sm leading-6 text-white outline-none transition placeholder:text-zinc-600 focus:border-violet-500"
                />

                <p className="mt-2 text-right text-xs text-zinc-600">
                  {description.length}/10000 characters
                </p>
              </div>

              <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">

                <div>
                  <label className="mb-2 block text-sm font-medium text-zinc-300">
                    Task Type
                  </label>

                  <select
                    value={taskType}
                    onChange={(e) => setTaskType(e.target.value)}
                    className="w-full rounded-lg border border-[#30303a] bg-[#151519] px-4 py-3 text-sm text-white outline-none focus:border-violet-500"
                  >
                    <option value="feature">New Feature</option>
                    <option value="bug">Bug Fix</option>
                    <option value="refactor">Code Refactoring</option>
                    <option value="testing">Testing</option>
                    <option value="documentation">Documentation</option>
                  </select>
                </div>

                <div>
                  <label className="mb-2 block text-sm font-medium text-zinc-300">
                    Priority
                  </label>

                  <select
                    value={priority}
                    onChange={(e) => setPriority(e.target.value)}
                    className="w-full rounded-lg border border-[#30303a] bg-[#151519] px-4 py-3 text-sm text-white outline-none focus:border-violet-500"
                  >
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                    <option value="critical">Critical</option>
                  </select>
                </div>

              </div>
            </div>
          </section>

          {/* Repository */}
          <section className="dashboard-card p-6">
            <div className="mb-6 flex items-center gap-3">
              <div className="rounded-lg bg-zinc-500/10 p-2">
                <Code2  size={19} className="text-white" />
              </div>

              <div>
                <h2 className="text-sm font-semibold text-white">
                  Repository Configuration
                </h2>
                <p className="mt-1 text-xs text-zinc-500">
                  Connect the GitHub repository for this task.
                </p>
              </div>
            </div>

            <div className="space-y-5">

              <div>
                <label className="mb-2 block text-sm font-medium text-zinc-300">
                  GitHub Repository URL{" "}
                  <span className="text-red-400">*</span>
                </label>

                <div className="relative">
                  <Code2 
                    size={17}
                    className="absolute left-4 top-3.5 text-zinc-500"
                  />

                  <input
                    value={repositoryUrl}
                    onChange={(e) => setRepositoryUrl(e.target.value)}
                    placeholder="https://github.com/username/repository"
                    type="url"
                    required
                    className="w-full rounded-lg border border-[#30303a] bg-[#151519] py-3 pl-11 pr-4 text-sm text-white outline-none focus:border-violet-500 placeholder:text-zinc-600"
                  />
                </div>
              </div>

              <div>
                <label className="mb-2 block text-sm font-medium text-zinc-300">
                  Target Branch
                </label>

                <div className="relative">
                  <GitBranch
                    size={17}
                    className="absolute left-4 top-3.5 text-zinc-500"
                  />

                  <input
                    value={branch}
                    onChange={(e) => setBranch(e.target.value)}
                    placeholder="main"
                    required
                    className="w-full rounded-lg border border-[#30303a] bg-[#151519] py-3 pl-11 pr-4 text-sm text-white outline-none focus:border-violet-500"
                  />
                </div>
              </div>

            </div>

            <div className="mt-5 flex gap-3 rounded-lg border border-blue-500/20 bg-blue-500/5 p-4">
              <Info size={17} className="shrink-0 text-blue-400" />

              <p className="text-xs leading-5 text-zinc-400">
                The repository must be accessible to ForgeAI. Private
                repository access and GitHub authentication will be
                configured during backend integration.
              </p>
            </div>
          </section>

          {/* Agent information */}
          <section className="dashboard-card p-5">
            <div className="flex items-center gap-3">
              <div className="rounded-lg bg-violet-500/10 p-3">
                <Bot size={21} className="text-violet-400" />
              </div>

              <div>
                <h3 className="text-sm font-semibold text-white">
                  Autonomous Agent Workflow
                </h3>

                <p className="mt-1 text-xs text-zinc-500">
                  ForgeAI will coordinate planning, development and
                  review agents according to your task configuration.
                </p>
              </div>
            </div>
          </section>

          {/* Errors */}
          {error && (
            <div
              role="alert"
              className="rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-400"
            >
              {error}
            </div>
          )}

          {/* Actions */}
          <div className="flex flex-col-reverse justify-between gap-3 sm:flex-row">
            <Link
              href="/dashboard"
              className="rounded-lg border border-[#30303a] px-5 py-3 text-center text-sm text-zinc-400 transition hover:bg-[#19191f] hover:text-white"
            >
              Cancel
            </Link>

            <button
              type="submit"
              disabled={submitting}
              className="flex items-center justify-center gap-2 rounded-lg bg-violet-600 px-6 py-3 text-sm font-medium text-white transition hover:bg-violet-500 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {submitting ? (
                <>
                  <Loader2 size={17} className="animate-spin" />
                  Preparing Task...
                </>
              ) : (
                <>
                  Create Task
                  <ArrowRight size={17} />
                </>
              )}
            </button>
          </div>

        </form>

        <div className="mt-5 flex items-center justify-center gap-2 text-xs text-zinc-600">
          <CheckCircle2 size={14} />
          Task configuration is prepared locally until backend integration.
        </div>
      </div>
    </DashboardLayout>
  );
}

"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import DashboardLayout from "@/components/layout/dashboard-layout";
import { ArrowLeft, Bot, CheckCircle2, Clock3, Code2, Loader2, Play, RefreshCw, XCircle } from "lucide-react";
import { api, type AgentRun, type Task } from "@/lib/api";

const terminal = ["succeeded", "failed", "rejected"];

export default function TaskDetailsPage() {
  const params = useParams<{ taskId: string }>();
  const [task, setTask] = useState<Task | null>(null);
  const [run, setRun] = useState<AgentRun | null>(null);
  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState("");

  const refreshRun = useCallback(async (runId: string) => {
    const latest = await api.getRun(runId);
    setRun(latest);
    return latest;
  }, []);

  useEffect(() => {
    Promise.all([api.getTask(params.taskId), api.listRuns(params.taskId)])
      .then(([loadedTask, runs]) => {
        setTask(loadedTask);
        if (runs.length) setRun(runs[0]);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Unable to load task."))
      .finally(() => setLoading(false));
  }, [params.taskId]);

  useEffect(() => {
    if (!run || terminal.includes(run.status.toLowerCase()) || run.status.toLowerCase() === "awaiting_approval") return;
    const timer = window.setInterval(() => {
      refreshRun(run.id).catch((err) => setError(err instanceof Error ? err.message : "Unable to refresh run."));
    }, 3000);
    return () => window.clearInterval(timer);
  }, [run, refreshRun]);

  async function executeTask() {
    setError("");
    setStarting(true);
    try {
      const createdRun = await api.startRun(params.taskId);
      setRun(createdRun);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to start agent run.");
    } finally {
      setStarting(false);
    }
  }

  if (loading) return <DashboardLayout><div className="flex min-h-[400px] items-center justify-center"><Loader2 className="animate-spin text-violet-400" /></div></DashboardLayout>;
  if (!task) return <DashboardLayout><div className="dashboard-card p-10 text-center"><h2 className="text-lg font-semibold text-white">Task not found</h2><p className="mt-2 text-sm text-zinc-500">{error}</p><Link href="/tasks" className="mt-5 inline-block text-violet-400">Back to Tasks</Link></div></DashboardLayout>;

  const status = run?.status || "not_started";
  const running = ["pending", "running", "executing"].includes(status.toLowerCase());

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <Link href="/tasks" className="inline-flex items-center gap-2 text-sm text-zinc-500 hover:text-white"><ArrowLeft size={15} />Back to Tasks</Link>
        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-start">
          <div><p className="text-xs uppercase tracking-wider text-violet-400">Engineering task</p><h1 className="mt-2 text-2xl font-bold text-white">{task.title}</h1><p className="mt-2 max-w-3xl whitespace-pre-wrap text-sm leading-6 text-zinc-400">{task.description}</p></div>
          <button onClick={executeTask} disabled={starting || running} className="inline-flex shrink-0 items-center justify-center gap-2 rounded-lg bg-violet-600 px-5 py-3 text-sm font-medium text-white hover:bg-violet-500 disabled:opacity-50">
            {starting || running ? <Loader2 size={16} className="animate-spin" /> : <Play size={16} />}
            {starting ? "Starting..." : running ? "Agent Running" : run ? "Run Again" : "Execute Agent"}
          </button>
        </div>

        {error && <div role="alert" className="rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-400">{error}</div>}

        <section className="grid gap-4 sm:grid-cols-2">
          <div className="dashboard-card p-5"><div className="flex items-center gap-2 text-xs text-zinc-500"><Code2 size={15}/>Repository</div><a className="mt-3 block break-all text-sm text-violet-400" href={task.repository_url} target="_blank" rel="noreferrer">{task.repository_url}</a></div>
          <div className="dashboard-card p-5"><div className="flex items-center gap-2 text-xs text-zinc-500"><Clock3 size={15}/>Task status</div><p className="mt-3 text-sm capitalize text-white">{task.status}</p></div>
        </section>

        <section className="dashboard-card p-6">
          <div className="flex items-center justify-between gap-3"><div><h2 className="text-sm font-semibold text-white">Agent execution</h2><p className="mt-1 text-xs text-zinc-500">Live status retrieved from the ForgeAI API</p></div><Bot className="text-violet-400" size={20}/></div>
          {run ? (
            <div className="mt-5 rounded-xl border border-[#30303a] bg-[#151519] p-5">
              <div className="flex flex-wrap items-center justify-between gap-3"><div><p className="text-xs text-zinc-500">Run ID</p><p className="mt-1 break-all font-mono text-xs text-zinc-300">{run.id}</p></div><span className="rounded-md bg-violet-500/10 px-3 py-1.5 text-xs capitalize text-violet-300">{run.status.replaceAll("_", " ")}</span></div>
              <p className="mt-4 text-xs text-zinc-500">Last updated: {new Date(run.updated_at).toLocaleString()}</p>
              {running && <p className="mt-3 flex items-center gap-2 text-xs text-blue-300"><RefreshCw size={13} className="animate-spin"/>Refreshing every 3 seconds</p>}
              {run.status.toLowerCase() === "succeeded" && <p className="mt-4 flex items-center gap-2 text-sm text-emerald-400"><CheckCircle2 size={16}/>Workflow completed successfully.</p>}
              {["failed", "rejected"].includes(run.status.toLowerCase()) && <p className="mt-4 flex items-center gap-2 text-sm text-red-400"><XCircle size={16}/>Workflow ended with status: {run.status}.</p>}
              {run.status.toLowerCase() === "awaiting_approval" && <p className="mt-4 text-sm text-amber-300">Human approval is required. Open Code Reviews to inspect pending approvals.</p>}
            </div>
          ) : (
            <div className="mt-5 rounded-xl border border-dashed border-[#30303a] p-10 text-center"><Clock3 className="mx-auto mb-3 text-zinc-500" size={25}/><p className="text-sm text-zinc-300">No agent run has been started.</p><p className="mt-1 text-xs text-zinc-500">Select Execute Agent to start the workflow.</p></div>
          )}
        </section>
      </div>
    </DashboardLayout>
  );
}

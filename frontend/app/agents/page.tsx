
"use client";

import { useState } from "react";
import Link from "next/link";
import DashboardLayout from "@/components/layout/dashboard-layout";
import {
  Bot,
  BrainCircuit,
  Code2,
  ShieldCheck,
  TestTube2,
  Activity,
  Loader2,
  Clock3,
  CheckCircle2,
  AlertCircle,
  CircleDot,
  ArrowUpRight,
  Play,
  Terminal,
  Cpu,
  Zap,
  ChevronRight,
  Search,
} from "lucide-react";

type AgentStatus = "Active" | "Idle" | "Completed" | "Failed";

type Agent = {
  id: string;
  name: string;
  role: string;
  description: string;
  status: AgentStatus;
  icon: typeof Bot;
  color: string;
  background: string;
  model: string;
  executions: number;
  successRate: string;
};

const agents: Agent[] = [
  {
    id: "planner",
    name: "Planner Agent",
    role: "Task Analysis & Planning",
    description:
      "Analyzes engineering requirements, understands the repository and creates structured implementation plans.",
    status: "Completed",
    icon: BrainCircuit,
    color: "text-violet-400",
    background: "bg-violet-500/10",
    model: "LLM Planner",
    executions: 24,
    successRate: "96%",
  },
  {
    id: "developer",
    name: "Developer Agent",
    role: "Code Generation",
    description:
      "Implements engineering tasks, generates code, modifies existing files and follows the execution plan.",
    status: "Active",
    icon: Code2,
    color: "text-blue-400",
    background: "bg-blue-500/10",
    model: "LLM Developer",
    executions: 21,
    successRate: "91%",
  },
  {
    id: "reviewer",
    name: "Reviewer Agent",
    role: "Code Review",
    description:
      "Analyzes generated code, identifies potential bugs and checks implementation quality.",
    status: "Idle",
    icon: ShieldCheck,
    color: "text-emerald-400",
    background: "bg-emerald-500/10",
    model: "LLM Reviewer",
    executions: 18,
    successRate: "94%",
  },
  {
    id: "testing",
    name: "Testing Agent",
    role: "Test Execution",
    description:
      "Executes tests, validates expected behavior and reports errors or failing test cases.",
    status: "Idle",
    icon: TestTube2,
    color: "text-amber-400",
    background: "bg-amber-500/10",
    model: "Test Runner",
    executions: 16,
    successRate: "88%",
  },
];

const executionLogs = [
  {
    time: "10:42:18",
    agent: "Developer Agent",
    event: "Analyzing existing authentication module",
    type: "info",
  },
  {
    time: "10:41:52",
    agent: "Planner Agent",
    event: "Implementation plan generated",
    type: "success",
  },
  {
    time: "10:41:20",
    agent: "Planner Agent",
    event: "Repository structure analyzed",
    type: "success",
  },
  {
    time: "10:40:45",
    agent: "System",
    event: "Task TSK-024 received",
    type: "info",
  },
  {
    time: "10:39:12",
    agent: "Testing Agent",
    event: "Previous test execution failed",
    type: "error",
  },
];

const activities = [
  {
    title: "Implementation plan generated",
    agent: "Planner Agent",
    time: "2 minutes ago",
    status: "Completed",
  },
  {
    title: "Code generation started",
    agent: "Developer Agent",
    time: "1 minute ago",
    status: "Active",
  },
  {
    title: "Awaiting code review",
    agent: "Reviewer Agent",
    time: "Pending",
    status: "Idle",
  },
];

function StatusBadge({ status }: { status: AgentStatus }) {
  const styles: Record<AgentStatus, string> = {
    Active: "bg-blue-500/10 text-blue-400 border-blue-500/20",
    Idle: "bg-zinc-500/10 text-zinc-400 border-zinc-500/20",
    Completed:
      "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
    Failed: "bg-red-500/10 text-red-400 border-red-500/20",
  };

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-[11px] font-medium ${styles[status]}`}
    >
      <span
        className={`h-1.5 w-1.5 rounded-full ${
          status === "Active"
            ? "animate-pulse bg-blue-400"
            : status === "Completed"
              ? "bg-emerald-400"
              : status === "Failed"
                ? "bg-red-400"
                : "bg-zinc-500"
        }`}
      />
      {status}
    </span>
  );
}

export default function AgentsPage() {
  const [filter, setFilter] = useState("All");
  const [search, setSearch] = useState("");

  const filteredAgents = agents.filter((agent) => {
    const matchesFilter =
      filter === "All" || agent.status === filter;

    const matchesSearch =
      agent.name.toLowerCase().includes(search.toLowerCase()) ||
      agent.role.toLowerCase().includes(search.toLowerCase());

    return matchesFilter && matchesSearch;
  });

  const activeCount = agents.filter(
    (agent) => agent.status === "Active"
  ).length;

  return (
    <DashboardLayout>
      <div className="space-y-7">

        {/* Page heading */}
        <section className="flex flex-col justify-between gap-5 sm:flex-row sm:items-center">
          <div>
            <div className="mb-2 flex items-center gap-2">
              <Activity size={16} className="text-violet-400" />
              <span className="text-xs font-medium tracking-wider text-violet-400">
                AGENT ORCHESTRATION
              </span>
            </div>

            <h1 className="text-2xl font-bold text-white">
              AI Agent Monitoring
            </h1>

            <p className="mt-2 text-sm text-zinc-500">
              Monitor your autonomous agents and their execution activities.
            </p>
          </div>

          <div className="flex items-center gap-2 rounded-lg border border-emerald-500/20 bg-emerald-500/5 px-4 py-2.5">
            <span className="h-2 w-2 animate-pulse rounded-full bg-emerald-400" />
            <span className="text-xs font-medium text-emerald-400">
              Monitoring Interface
            </span>
          </div>
        </section>

        {/* Statistics */}
        <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {[
            {
              title: "Total Agents",
              value: "04",
              description: "Configured agents",
              icon: Bot,
              color: "text-violet-400",
              bg: "bg-violet-500/10",
            },
            {
              title: "Active Agents",
              value: String(activeCount).padStart(2, "0"),
              description: "Currently marked active",
              icon: Activity,
              color: "text-blue-400",
              bg: "bg-blue-500/10",
            },
            {
              title: "Completed Runs",
              value: "18",
              description: "Sample execution data",
              icon: CheckCircle2,
              color: "text-emerald-400",
              bg: "bg-emerald-500/10",
            },
            {
              title: "Failed Runs",
              value: "02",
              description: "Sample execution data",
              icon: AlertCircle,
              color: "text-red-400",
              bg: "bg-red-500/10",
            },
          ].map((stat) => {
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

        {/* Agent cards */}
        <section>
          <div className="mb-5 flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
            <div>
              <h2 className="text-base font-semibold text-white">
                Registered Agents
              </h2>
              <p className="mt-1 text-xs text-zinc-500">
                Specialized agents in the engineering workflow
              </p>
            </div>

            <div className="relative">
              <Search
                size={15}
                className="absolute left-3 top-3 text-zinc-500"
              />

              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search agents..."
                className="w-full rounded-lg border border-[#30303a] bg-[#151519] py-2.5 pl-9 pr-4 text-xs text-white outline-none focus:border-violet-500 sm:w-56"
              />
            </div>
          </div>

          {/* Filters */}
          <div className="mb-5 flex flex-wrap gap-2">
            {["All", "Active", "Idle", "Completed", "Failed"].map(
              (status) => (
                <button
                  key={status}
                  onClick={() => setFilter(status)}
                  className={`rounded-lg px-3 py-2 text-xs transition ${
                    filter === status
                      ? "bg-violet-600 text-white"
                      : "border border-[#30303a] bg-[#151519] text-zinc-400 hover:text-white"
                  }`}
                >
                  {status}
                </button>
              )
            )}
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            {filteredAgents.map((agent) => {
              const Icon = agent.icon;

              return (
                <div key={agent.id} className="dashboard-card p-5">
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <div className={`rounded-xl p-3 ${agent.background}`}>
                        <Icon size={22} className={agent.color} />
                      </div>

                      <div>
                        <h3 className="text-sm font-semibold text-white">
                          {agent.name}
                        </h3>

                        <p className="mt-1 text-xs text-zinc-500">
                          {agent.role}
                        </p>
                      </div>
                    </div>

                    <StatusBadge status={agent.status} />
                  </div>

                  <p className="mt-5 min-h-[48px] text-xs leading-6 text-zinc-400">
                    {agent.description}
                  </p>

                  <div className="mt-5 grid grid-cols-3 gap-3 border-t border-[#27272f] pt-5">
                    <div>
                      <p className="text-[10px] text-zinc-500">
                        Executions
                      </p>
                      <p className="mt-1 text-sm font-semibold text-white">
                        {agent.executions}
                      </p>
                    </div>

                    <div>
                      <p className="text-[10px] text-zinc-500">
                        Success Rate
                      </p>
                      <p className="mt-1 text-sm font-semibold text-emerald-400">
                        {agent.successRate}
                      </p>
                    </div>

                    <div>
                      <p className="text-[10px] text-zinc-500">
                        Runtime
                      </p>
                      <p className="mt-1 text-sm font-semibold text-white">
                        {agent.model}
                      </p>
                    </div>
                  </div>

                  <div className="mt-5 flex items-center justify-between">
                    <span className="flex items-center gap-1.5 text-[10px] text-zinc-500">
                      <Cpu size={13} />
                      Agent ID: {agent.id}
                    </span>

                    <button
                      onClick={() =>
                        alert(
                          `${agent.name}: Detailed monitoring will be connected to the backend.`
                        )
                      }
                      className="flex items-center gap-1 text-xs text-violet-400 hover:text-violet-300"
                    >
                      View details
                      <ArrowUpRight size={13} />
                    </button>
                  </div>
                </div>
              );
            })}

            {filteredAgents.length === 0 && (
              <div className="dashboard-card col-span-full p-10 text-center">
                <Bot size={30} className="mx-auto text-zinc-500" />
                <p className="mt-3 text-sm text-white">
                  No agents found
                </p>
                <p className="mt-1 text-xs text-zinc-500">
                  Try changing your search or status filter.
                </p>
              </div>
            )}
          </div>
        </section>

        {/* Execution overview */}
        <section className="grid grid-cols-1 gap-5 xl:grid-cols-2">

          {/* Workflow */}
          <div className="dashboard-card p-5">
            <div className="mb-6 flex items-center justify-between">
              <div>
                <h2 className="text-sm font-semibold text-white">
                  Current Execution
                </h2>

                <p className="mt-1 text-xs text-zinc-500">
                  Example agent workflow
                </p>
              </div>

              <span className="rounded-md bg-blue-500/10 px-2.5 py-1 text-[10px] text-blue-400">
                TSK-024
              </span>
            </div>

            <div className="space-y-5">
              {activities.map((activity, index) => (
                <div key={activity.title} className="flex gap-3">
                  <div className="flex flex-col items-center">
                    <div
                      className={`flex h-8 w-8 items-center justify-center rounded-lg ${
                        activity.status === "Completed"
                          ? "bg-emerald-500/10"
                          : activity.status === "Active"
                            ? "bg-blue-500/10"
                            : "bg-zinc-500/10"
                      }`}
                    >
                      {activity.status === "Completed" ? (
                        <CheckCircle2
                          size={16}
                          className="text-emerald-400"
                        />
                      ) : activity.status === "Active" ? (
                        <Loader2
                          size={16}
                          className="animate-spin text-blue-400"
                        />
                      ) : (
                        <Clock3 size={16} className="text-zinc-500" />
                      )}
                    </div>

                    {index !== activities.length - 1 && (
                      <div className="mt-1 h-6 w-px bg-[#30303a]" />
                    )}
                  </div>

                  <div className="flex-1">
                    <p className="text-xs font-medium text-zinc-200">
                      {activity.title}
                    </p>

                    <p className="mt-1 text-[11px] text-zinc-500">
                      {activity.agent}
                    </p>
                  </div>

                  <span className="text-[10px] text-zinc-500">
                    {activity.time}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Runtime information */}
          <div className="dashboard-card p-5">
            <div className="mb-5 flex items-center gap-2">
              <Zap size={17} className="text-amber-400" />
              <h2 className="text-sm font-semibold text-white">
                Runtime Overview
              </h2>
            </div>

            <div className="space-y-4">
              {[
                { label: "Agent Orchestration", value: "Configured" },
                { label: "Task Execution", value: "Pending integration" },
                { label: "LLM Provider", value: "Backend managed" },
                { label: "Tool Execution", value: "Backend managed" },
              ].map((item) => (
                <div
                  key={item.label}
                  className="flex items-center justify-between border-b border-[#27272f] pb-3 last:border-0"
                >
                  <span className="text-xs text-zinc-400">
                    {item.label}
                  </span>

                  <span className="text-xs text-zinc-300">
                    {item.value}
                  </span>
                </div>
              ))}
            </div>

            <div className="mt-5 rounded-lg border border-violet-500/20 bg-violet-500/5 p-4">
              <div className="flex items-center gap-2">
                <Bot size={17} className="text-violet-400" />
                <p className="text-xs font-medium text-violet-300">
                  Backend Integration
                </p>
              </div>

              <p className="mt-2 text-xs leading-5 text-zinc-400">
                Live agent status, execution metrics and runtime logs
                will be supplied by the ForgeAI orchestration backend.
              </p>
            </div>
          </div>
        </section>

        {/* Execution logs */}
        <section className="dashboard-card overflow-hidden">
          <div className="flex items-center justify-between border-b border-[#27272f] p-5">
            <div className="flex items-center gap-3">
              <Terminal size={18} className="text-violet-400" />
              <div>
                <h2 className="text-sm font-semibold text-white">
                  Agent Execution Logs
                </h2>
                <p className="mt-1 text-xs text-zinc-500">
                  Sample execution events
                </p>
              </div>
            </div>

            <span className="rounded-md bg-zinc-500/10 px-2 py-1 text-[10px] text-zinc-400">
              Mock data
            </span>
          </div>

          <div className="overflow-x-auto bg-[#0b0b0e] p-5">
            <div className="min-w-[600px] space-y-4 font-mono text-xs">
              {executionLogs.map((log, index) => (
                <div key={index} className="flex gap-4">
                  <span className="text-zinc-600">
                    {log.time}
                  </span>

                  <span
                    className={`w-32 shrink-0 ${
                      log.agent === "System"
                        ? "text-violet-400"
                        : "text-blue-400"
                    }`}
                  >
                    [{log.agent}]
                  </span>

                  <span
                    className={
                      log.type === "success"
                        ? "text-emerald-400"
                        : log.type === "error"
                          ? "text-red-400"
                          : "text-zinc-400"
                    }
                  >
                    {log.event}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Navigation */}
        <div className="flex flex-wrap justify-between gap-3">
          <Link
            href="/tasks"
            className="flex items-center gap-2 rounded-lg border border-[#30303a] px-4 py-2.5 text-xs text-zinc-400 hover:bg-[#19191f] hover:text-white"
          >
            <Clock3 size={15} />
            View Tasks
          </Link>

          <Link
            href="/reviews"
            className="flex items-center gap-2 rounded-lg bg-violet-600 px-4 py-2.5 text-xs font-medium text-white hover:bg-violet-500"
          >
            Open Code Reviews
            <ArrowUpRight size={15} />
          </Link>
        </div>

      </div>
    </DashboardLayout>
  );
}

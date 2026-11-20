
"use client";

import { useMemo, useState } from "react";
import {
  Activity,
  AlertCircle,
  ArrowDown,
  ArrowLeft,
  ArrowRight,
  Check,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Clock3,
  Code2,
  FileCode2,
  GitBranch,
  MessageSquare,
  Search,
  ShieldCheck,
  Sparkles,
  X,
  XCircle,
} from "lucide-react";

import DashboardLayout from "@/components/layout/dashboard-layout";

type ReviewStatus = "Pending" | "Approved" | "Changes Requested" | "Rejected";
type Severity = "Critical" | "High" | "Medium" | "Low";

type Finding = {
  id: number;
  severity: Severity;
  title: string;
  description: string;
  file: string;
  line: number;
  recommendation: string;
};

type Review = {
  id: number;
  title: string;
  repository: string;
  branch: string;
  author: string;
  initials: string;
  status: ReviewStatus;
  time: string;
  filesChanged: number;
  additions: number;
  deletions: number;
  score: number;
  findings: Finding[];
};

const initialReviews: Review[] = [
  {
    id: 1,
    title: "Add JWT authentication middleware",
    repository: "forgeai/backend",
    branch: "feature/jwt-auth",
    author: "Rahul Sharma",
    initials: "RS",
    status: "Pending",
    time: "12 minutes ago",
    filesChanged: 4,
    additions: 86,
    deletions: 12,
    score: 78,
    findings: [
      {
        id: 1,
        severity: "Critical",
        title: "JWT secret is not validated",
        description:
          "The middleware reads the JWT secret from environment variables without checking whether the value exists.",
        file: "app/middleware/auth.py",
        line: 18,
        recommendation:
          "Validate the secret during application startup and fail safely when it is missing.",
      },
      {
        id: 2,
        severity: "High",
        title: "Token expiration is not handled",
        description:
          "Expired tokens may raise an exception that is not handled by the current middleware.",
        file: "app/middleware/auth.py",
        line: 34,
        recommendation:
          "Handle token expiration explicitly and return an HTTP 401 response.",
      },
      {
        id: 3,
        severity: "Medium",
        title: "Missing authentication test cases",
        description:
          "The current change does not include tests for invalid tokens and expired tokens.",
        file: "tests/test_auth.py",
        line: 1,
        recommendation:
          "Add tests for missing, malformed, invalid, and expired JWT tokens.",
      },
    ],
  },
  {
    id: 2,
    title: "Implement task execution endpoint",
    repository: "forgeai/backend",
    branch: "feature/task-execution",
    author: "Priya Patel",
    initials: "PP",
    status: "Pending",
    time: "38 minutes ago",
    filesChanged: 6,
    additions: 142,
    deletions: 28,
    score: 91,
    findings: [
      {
        id: 4,
        severity: "Medium",
        title: "Potentially missing timeout",
        description:
          "The task execution operation does not show a timeout for long-running execution.",
        file: "app/api/tasks.py",
        line: 72,
        recommendation:
          "Add a configurable execution timeout and return a clear task status.",
      },
      {
        id: 5,
        severity: "Low",
        title: "Improve logging context",
        description:
          "Execution logs could include the task ID to make debugging easier.",
        file: "app/services/executor.py",
        line: 45,
        recommendation:
          "Include the task ID and execution attempt in structured logs.",
      },
    ],
  },
  {
    id: 3,
    title: "Update database connection handling",
    repository: "forgeai/backend",
    branch: "fix/db-connection",
    author: "Amit Verma",
    initials: "AV",
    status: "Approved",
    time: "2 hours ago",
    filesChanged: 2,
    additions: 34,
    deletions: 9,
    score: 96,
    findings: [],
  },
  {
    id: 4,
    title: "Add repository validation",
    repository: "forgeai/backend",
    branch: "feature/repo-validation",
    author: "Neha Joshi",
    initials: "NJ",
    status: "Changes Requested",
    time: "Yesterday",
    filesChanged: 3,
    additions: 65,
    deletions: 14,
    score: 63,
    findings: [
      {
        id: 6,
        severity: "High",
        title: "Repository URL is not validated",
        description:
          "The submitted repository URL is accepted without checking its format or host.",
        file: "app/services/repository.py",
        line: 22,
        recommendation:
          "Validate the repository host and owner/repository path before processing.",
      },
    ],
  },
];

const diffLines = [
  { type: "context", number: 1, old: 1, content: "from fastapi import Request, HTTPException" },
  { type: "context", number: 2, old: 2, content: "from jose import jwt" },
  { type: "context", number: 3, old: 3, content: "import os" },
  { type: "context", number: 4, old: 4, content: "" },
  { type: "context", number: 5, old: 5, content: "async def authenticate(request: Request):" },
  { type: "context", number: 6, old: 6, content: '    token = request.headers.get("Authorization")' },
  { type: "remove", number: 7, old: 7, content: '    secret = os.getenv("JWT_SECRET")' },
  { type: "add", number: 7, old: "", content: '    secret = os.getenv("JWT_SECRET", "")' },
  { type: "add", number: 8, old: "", content: '    if not secret:' },
  { type: "add", number: 9, old: "", content: '        raise HTTPException(status_code=500, detail="JWT configuration missing")' },
  { type: "context", number: 10, old: 8, content: "    if not token:" },
  { type: "context", number: 11, old: 9, content: '        raise HTTPException(status_code=401, detail="Missing token")' },
  { type: "context", number: 12, old: 10, content: "" },
  { type: "remove", number: 13, old: 11, content: '    payload = jwt.decode(token, secret, algorithms=["HS256"])' },
  { type: "add", number: 13, old: "", content: '    try:' },
  { type: "add", number: 14, old: "", content: '        payload = jwt.decode(token, secret, algorithms=["HS256"])' },
  { type: "add", number: 15, old: "", content: "    except Exception:" },
  { type: "add", number: 16, old: "", content: '        raise HTTPException(status_code=401, detail="Invalid token")' },
  { type: "context", number: 17, old: 12, content: "    return payload" },
];

const severityStyles: Record<Severity, string> = {
  Critical: "border-red-500/30 bg-red-500/10 text-red-400",
  High: "border-orange-500/30 bg-orange-500/10 text-orange-400",
  Medium: "border-yellow-500/30 bg-yellow-500/10 text-yellow-400",
  Low: "border-blue-500/30 bg-blue-500/10 text-blue-400",
};

const statusStyles: Record<ReviewStatus, string> = {
  Pending: "border-yellow-500/30 bg-yellow-500/10 text-yellow-400",
  Approved: "border-green-500/30 bg-green-500/10 text-green-400",
  "Changes Requested": "border-orange-500/30 bg-orange-500/10 text-orange-400",
  Rejected: "border-red-500/30 bg-red-500/10 text-red-400",
};

export default function ReviewsPage() {
  const [reviews, setReviews] = useState(initialReviews);
  const [selectedId, setSelectedId] = useState(1);
  const [filter, setFilter] = useState("All");
  const [search, setSearch] = useState("");
  const [activeFinding, setActiveFinding] = useState<number | null>(1);
  const [showAllFindings, setShowAllFindings] = useState(true);
  const [feedback, setFeedback] = useState("");

  const selectedReview = reviews.find((review) => review.id === selectedId);

  const filteredReviews = useMemo(() => {
    return reviews.filter((review) => {
      const matchesFilter = filter === "All" || review.status === filter;
      const matchesSearch =
        review.title.toLowerCase().includes(search.toLowerCase()) ||
        review.repository.toLowerCase().includes(search.toLowerCase()) ||
        review.author.toLowerCase().includes(search.toLowerCase());

      return matchesFilter && matchesSearch;
    });
  }, [reviews, filter, search]);

  const pendingCount = reviews.filter((r) => r.status === "Pending").length;
  const approvedCount = reviews.filter((r) => r.status === "Approved").length;
  const findingsCount = reviews.reduce((total, r) => total + r.findings.length, 0);

  function updateReviewStatus(status: ReviewStatus) {
    if (!selectedReview) return;

    setReviews((current) =>
      current.map((review) =>
        review.id === selectedId ? { ...review, status } : review
      )
    );

    setFeedback(`Review marked as "${status}". This is a local UI demonstration.`);
  }

  return (
    <DashboardLayout>
      <div className="space-y-6 pb-10">
        {/* Page heading */}
        <div className="flex flex-col justify-between gap-4 md:flex-row md:items-center">
          <div>
            <div className="mb-2 flex items-center gap-2 text-sm text-zinc-500">
              <span>Workspace</span>
              <ChevronRight size={14} />
              <span className="text-zinc-300">Code Reviews</span>
            </div>
            <h1 className="text-2xl font-semibold text-white">Code Reviews</h1>
            <p className="mt-1 text-sm text-zinc-400">
              Inspect AI-generated findings and make human review decisions.
            </p>
          </div>

          <div className="flex items-center gap-2 rounded-lg border border-violet-500/20 bg-violet-500/10 px-3 py-2 text-sm text-violet-300">
            <Sparkles size={16} />
            AI Review Center
          </div>
        </div>

        {/* Summary cards */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <SummaryCard
            label="Total Reviews"
            value={reviews.length.toString().padStart(2, "0")}
            detail="All submitted reviews"
            icon={<Code2 size={19} />}
          />
          <SummaryCard
            label="Pending Reviews"
            value={pendingCount.toString().padStart(2, "0")}
            detail="Awaiting human decision"
            icon={<Clock3 size={19} />}
            accent="text-yellow-400"
          />
          <SummaryCard
            label="Approved"
            value={approvedCount.toString().padStart(2, "0")}
            detail="Approved in this demo"
            icon={<CheckCircle2 size={19} />}
            accent="text-green-400"
          />
          <SummaryCard
            label="AI Findings"
            value={findingsCount.toString().padStart(2, "0")}
            detail="Across all review examples"
            icon={<ShieldCheck size={19} />}
            accent="text-violet-400"
          />
        </div>

        {/* Main review workspace */}
        <div className="grid min-w-0 grid-cols-1 gap-5 xl:grid-cols-[340px_minmax(0,1fr)]">
          {/* Review queue */}
          <section className="dashboard-card min-w-0 overflow-hidden rounded-xl border border-[#27272f] bg-[#111114]">
            <div className="border-b border-[#27272f] p-4">
              <div className="flex items-center justify-between">
                <h2 className="font-semibold text-white">Review Queue</h2>
                <span className="rounded-md bg-zinc-800 px-2 py-1 text-xs text-zinc-400">
                  {filteredReviews.length} reviews
                </span>
              </div>

              <div className="relative mt-4">
                <Search
                  size={16}
                  className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500"
                />
                <input
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                  placeholder="Search reviews..."
                  className="w-full rounded-lg border border-[#303039] bg-[#09090b] py-2.5 pl-9 pr-3 text-sm text-white outline-none placeholder:text-zinc-600 focus:border-violet-500"
                />
              </div>

              <div className="mt-3 flex flex-wrap gap-1.5">
                {["All", "Pending", "Approved", "Changes Requested", "Rejected"].map(
                  (item) => (
                    <button
                      key={item}
                      onClick={() => setFilter(item)}
                      className={`rounded-md px-2.5 py-1.5 text-xs transition ${
                        filter === item
                          ? "bg-violet-500/20 text-violet-300"
                          : "bg-zinc-900 text-zinc-500 hover:text-zinc-300"
                      }`}
                    >
                      {item}
                    </button>
                  )
                )}
              </div>
            </div>

            <div className="divide-y divide-[#27272f]">
              {filteredReviews.map((review) => (
                <button
                  key={review.id}
                  onClick={() => {
                    setSelectedId(review.id);
                    setActiveFinding(review.findings[0]?.id ?? null);
                    setFeedback("");
                  }}
                  className={`w-full p-4 text-left transition hover:bg-white/[0.03] ${
                    selectedId === review.id
                      ? "border-l-2 border-violet-500 bg-violet-500/[0.06]"
                      : "border-l-2 border-transparent"
                  }`}
                >
                  <div className="mb-2 flex items-start justify-between gap-2">
                    <span className="line-clamp-2 text-sm font-medium text-zinc-200">
                      {review.title}
                    </span>
                    <ChevronRight
                      size={15}
                      className="mt-0.5 shrink-0 text-zinc-600"
                    />
                  </div>

                  <div className="flex items-center gap-1.5 text-xs text-zinc-500">
                    <Code2 size={13} />
                    {review.repository}
                  </div>

                  <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
                    <span
                      className={`rounded-md border px-2 py-1 text-[10px] ${statusStyles[review.status]}`}
                    >
                      {review.status}
                    </span>
                    <span className="text-[11px] text-zinc-600">{review.time}</span>
                  </div>

                  <div className="mt-3 flex items-center justify-between text-xs text-zinc-500">
                    <span>{review.author}</span>
                    <span>{review.findings.length} findings</span>
                  </div>
                </button>
              ))}

              {filteredReviews.length === 0 && (
                <div className="p-8 text-center text-sm text-zinc-500">
                  No reviews match your search.
                </div>
              )}
            </div>
          </section>

          {/* Selected review details */}
          <div className="min-w-0 space-y-5">
            {selectedReview ? (
              <>
                {/* Review header */}
                <section className="dashboard-card rounded-xl border border-[#27272f] bg-[#111114] p-5">
                  <div className="flex flex-col justify-between gap-4 lg:flex-row">
                    <div className="min-w-0">
                      <div className="mb-2 flex flex-wrap items-center gap-2">
                        <span className="rounded-md border border-violet-500/20 bg-violet-500/10 px-2 py-1 text-xs text-violet-300">
                          Pull Request #{selectedReview.id}
                        </span>
                        <span
                          className={`rounded-md border px-2 py-1 text-xs ${statusStyles[selectedReview.status]}`}
                        >
                          {selectedReview.status}
                        </span>
                      </div>

                      <h2 className="text-lg font-semibold text-white">
                        {selectedReview.title}
                      </h2>

                      <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-zinc-500">
                        <span className="flex items-center gap-1.5">
                          <Code2 size={13} />
                          {selectedReview.repository}
                        </span>
                        <span className="flex items-center gap-1.5">
                          <GitBranch size={13} />
                          {selectedReview.branch}
                        </span>
                        <span>{selectedReview.author}</span>
                      </div>
                    </div>

                    <div className="flex shrink-0 items-center gap-3 rounded-lg border border-[#303039] bg-[#09090b] px-4 py-3">
                      <div className="text-center">
                        <div className="text-2xl font-semibold text-white">
                          {selectedReview.score}
                        </div>
                        <div className="text-[10px] uppercase tracking-wider text-zinc-500">
                          AI Score
                        </div>
                      </div>
                      <div className="h-10 w-px bg-[#303039]" />
                      <div>
                        <div className="text-xs text-green-400">
                          +{selectedReview.additions}
                        </div>
                        <div className="text-xs text-red-400">
                          -{selectedReview.deletions}
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="mt-5 grid grid-cols-3 gap-3 border-t border-[#27272f] pt-4">
                    <Metric label="Files changed" value={selectedReview.filesChanged} />
                    <Metric label="Additions" value={`+${selectedReview.additions}`} green />
                    <Metric label="Deletions" value={`-${selectedReview.deletions}`} red />
                  </div>
                </section>

                {/* AI findings */}
                <section className="dashboard-card overflow-hidden rounded-xl border border-[#27272f] bg-[#111114]">
                  <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[#27272f] p-4">
                    <div className="flex items-center gap-2">
                      <div className="rounded-lg bg-violet-500/10 p-2 text-violet-300">
                        <Sparkles size={17} />
                      </div>
                      <div>
                        <h3 className="text-sm font-semibold text-white">
                          AI Review Findings
                        </h3>
                        <p className="text-xs text-zinc-500">
                          Example findings for this pull request
                        </p>
                      </div>
                    </div>

                    <button
                      onClick={() => setShowAllFindings((current) => !current)}
                      className="flex items-center gap-1 text-xs text-zinc-400 hover:text-white"
                    >
                      {showAllFindings ? "Collapse" : "Expand"}
                      <ChevronDown
                        size={14}
                        className={showAllFindings ? "rotate-180" : ""}
                      />
                    </button>
                  </div>

                  {showAllFindings && (
                    <div className="p-4">
                      {selectedReview.findings.length === 0 ? (
                        <div className="flex flex-col items-center py-8 text-center">
                          <CheckCircle2 size={30} className="text-green-400" />
                          <p className="mt-3 text-sm font-medium text-white">
                            No findings in this example
                          </p>
                          <p className="mt-1 text-xs text-zinc-500">
                            The review has no sample AI findings.
                          </p>
                        </div>
                      ) : (
                        <div className="space-y-3">
                          {selectedReview.findings.map((finding) => (
                            <button
                              key={finding.id}
                              onClick={() => setActiveFinding(finding.id)}
                              className={`w-full rounded-lg border p-4 text-left transition ${
                                activeFinding === finding.id
                                  ? "border-violet-500/40 bg-violet-500/[0.06]"
                                  : "border-[#303039] bg-[#0d0d10] hover:border-zinc-600"
                              }`}
                            >
                              <div className="flex flex-wrap items-center justify-between gap-2">
                                <div className="flex items-center gap-2">
                                  <AlertCircle
                                    size={16}
                                    className={
                                      finding.severity === "Critical" ||
                                      finding.severity === "High"
                                        ? "text-red-400"
                                        : "text-yellow-400"
                                    }
                                  />
                                  <span className="text-sm font-medium text-zinc-200">
                                    {finding.title}
                                  </span>
                                </div>
                                <span
                                  className={`rounded-md border px-2 py-1 text-[10px] ${severityStyles[finding.severity]}`}
                                >
                                  {finding.severity}
                                </span>
                              </div>

                              <p className="mt-2 text-xs leading-5 text-zinc-400">
                                {finding.description}
                              </p>

                              <div className="mt-3 flex flex-wrap items-center gap-2 text-[11px] text-zinc-500">
                                <FileCode2 size={13} />
                                {finding.file}
                                <span className="text-zinc-700">•</span>
                                Line {finding.line}
                              </div>

                              {activeFinding === finding.id && (
                                <div className="mt-4 rounded-lg border border-violet-500/20 bg-violet-500/[0.06] p-3">
                                  <p className="text-xs font-semibold text-violet-300">
                                    Suggested recommendation
                                  </p>
                                  <p className="mt-1 text-xs leading-5 text-zinc-300">
                                    {finding.recommendation}
                                  </p>
                                </div>
                              )}
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </section>

                {/* Code diff */}
                <section className="dashboard-card overflow-hidden rounded-xl border border-[#27272f] bg-[#111114]">
                  <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[#27272f] p-4">
                    <div>
                      <h3 className="text-sm font-semibold text-white">
                        Code Changes
                      </h3>
                      <p className="mt-1 text-xs text-zinc-500">
                        Example unified diff · app/middleware/auth.py
                      </p>
                    </div>
                    <div className="flex items-center gap-3 text-xs">
                      <span className="text-green-400">+ 5 added</span>
                      <span className="text-red-400">- 2 removed</span>
                    </div>
                  </div>

                  <div className="overflow-x-auto">
                    <div className="min-w-[650px] font-mono text-xs">
                      <div className="border-b border-[#27272f] bg-[#0b0b0e] px-4 py-2 text-zinc-500">
                        @@ -1,12 +1,17 @@
                      </div>

                      {diffLines.map((line, index) => (
                        <div
                          key={index}
                          className={`flex min-h-7 ${
                            line.type === "add"
                              ? "bg-green-500/[0.08]"
                              : line.type === "remove"
                                ? "bg-red-500/[0.08]"
                                : ""
                          }`}
                        >
                          <span className="w-10 shrink-0 select-none border-r border-[#27272f] px-2 py-1 text-right text-zinc-600">
                            {line.old}
                          </span>
                          <span className="w-10 shrink-0 select-none border-r border-[#27272f] px-2 py-1 text-right text-zinc-600">
                            {line.type === "remove" ? "" : line.number}
                          </span>
                          <span
                            className={`w-7 shrink-0 select-none px-2 py-1 text-center ${
                              line.type === "add"
                                ? "text-green-400"
                                : line.type === "remove"
                                  ? "text-red-400"
                                  : "text-zinc-700"
                            }`}
                          >
                            {line.type === "add" ? "+" : line.type === "remove" ? "-" : " "}
                          </span>
                          <code
                            className={`whitespace-pre px-2 py-1 ${
                              line.type === "add"
                                ? "text-green-300"
                                : line.type === "remove"
                                  ? "text-red-300"
                                  : "text-zinc-400"
                            }`}
                          >
                            {line.content || " "}
                          </code>
                        </div>
                      ))}
                    </div>
                  </div>
                </section>

                {/* Human review actions */}
                <section className="dashboard-card rounded-xl border border-[#27272f] bg-[#111114] p-5">
                  <div className="flex items-center gap-2">
                    <ShieldCheck size={18} className="text-violet-400" />
                    <h3 className="font-semibold text-white">Human Review Decision</h3>
                  </div>

                  <p className="mt-2 text-xs leading-5 text-zinc-500">
                    Review the code and AI findings before making a decision.
                    AI recommendations do not automatically approve or merge code.
                  </p>

                  <textarea
                    value={feedback}
                    onChange={(event) => setFeedback(event.target.value)}
                    placeholder="Add your review comments..."
                    rows={3}
                    className="mt-4 w-full resize-y rounded-lg border border-[#303039] bg-[#09090b] p-3 text-sm text-white outline-none placeholder:text-zinc-600 focus:border-violet-500"
                  />

                  <div className="mt-4 flex flex-wrap gap-2">
                    <button
                      onClick={() => updateReviewStatus("Approved")}
                      className="flex items-center gap-2 rounded-lg bg-green-600 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-green-500"
                    >
                      <Check size={16} />
                      Approve
                    </button>

                    <button
                      onClick={() => updateReviewStatus("Changes Requested")}
                      className="flex items-center gap-2 rounded-lg border border-orange-500/30 bg-orange-500/10 px-4 py-2.5 text-sm font-medium text-orange-300 transition hover:bg-orange-500/20"
                    >
                      <MessageSquare size={16} />
                      Request Changes
                    </button>

                    <button
                      onClick={() => updateReviewStatus("Rejected")}
                      className="flex items-center gap-2 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-2.5 text-sm font-medium text-red-300 transition hover:bg-red-500/20"
                    >
                      <XCircle size={16} />
                      Reject
                    </button>
                  </div>

                  <p className="mt-3 text-[11px] text-zinc-600">
                    Demo mode: decisions update local page state only. No GitHub
                    pull request, backend record, or repository is modified.
                  </p>
                </section>
              </>
            ) : (
              <div className="dashboard-card flex min-h-96 flex-col items-center justify-center rounded-xl border border-[#27272f] bg-[#111114] p-8 text-center">
                <Search size={30} className="text-zinc-600" />
                <h3 className="mt-4 font-medium text-white">No review selected</h3>
                <p className="mt-1 text-sm text-zinc-500">
                  Choose a review from the queue to inspect its details.
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Footer note */}
        <div className="flex items-start gap-2 rounded-lg border border-[#27272f] bg-[#111114] p-4 text-xs leading-5 text-zinc-500">
          <Activity size={16} className="mt-0.5 shrink-0 text-violet-400" />
          <p>
            All review records, AI findings, scores, and code diffs on this page
            are sample frontend data. The AI reviewer and repository integration
            will be connected after the backend integration phase.
          </p>
        </div>
      </div>
    </DashboardLayout>
  );
}

function SummaryCard({
  label,
  value,
  detail,
  icon,
  accent = "text-zinc-300",
}: {
  label: string;
  value: string;
  detail: string;
  icon: React.ReactNode;
  accent?: string;
}) {
  return (
    <div className="dashboard-card rounded-xl border border-[#27272f] bg-[#111114] p-5">
      <div className="flex items-center justify-between">
        <span className="text-sm text-zinc-400">{label}</span>
        <span className={accent}>{icon}</span>
      </div>
      <div className="mt-3 text-2xl font-semibold text-white">{value}</div>
      <p className="mt-1 text-xs text-zinc-600">{detail}</p>
    </div>
  );
}

function Metric({
  label,
  value,
  green,
  red,
}: {
  label: string;
  value: string | number;
  green?: boolean;
  red?: boolean;
}) {
  return (
    <div>
      <p className="text-xs text-zinc-500">{label}</p>
      <p
        className={`mt-1 text-lg font-semibold ${
          green ? "text-green-400" : red ? "text-red-400" : "text-white"
        }`}
      >
        {value}
      </p>
    </div>
  );
}

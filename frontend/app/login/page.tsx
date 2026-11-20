"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { Bot, Loader2 } from "lucide-react";
import { api } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const result = mode === "login"
        ? await api.login(email, password)
        : await api.register(email, password);
      localStorage.setItem("forgeai_access_token", result.access_token);
      router.replace("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Authentication failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-[#09090b] px-5">
      <form onSubmit={submit} className="w-full max-w-md rounded-2xl border border-[#30303a] bg-[#111115] p-8">
        <div className="mb-7 flex items-center gap-3"><div className="rounded-xl bg-violet-500/10 p-3"><Bot className="text-violet-400"/></div><div><h1 className="text-xl font-bold text-white">ForgeAI</h1><p className="text-xs text-zinc-500">Autonomous Engineering Agent</p></div></div>
        <h2 className="text-lg font-semibold text-white">{mode === "login" ? "Welcome back" : "Create your account"}</h2>
        <p className="mt-1 text-sm text-zinc-500">Sign in to manage your engineering tasks.</p>
        <label className="mt-6 block text-sm text-zinc-300">Email</label>
        <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} className="mt-2 w-full rounded-lg border border-[#30303a] bg-[#09090b] px-4 py-3 text-sm text-white outline-none focus:border-violet-500"/>
        <label className="mt-4 block text-sm text-zinc-300">Password</label>
        <input type="password" required minLength={mode === "register" ? 12 : 1} value={password} onChange={(e) => setPassword(e.target.value)} className="mt-2 w-full rounded-lg border border-[#30303a] bg-[#09090b] px-4 py-3 text-sm text-white outline-none focus:border-violet-500"/>
        {error && <p role="alert" className="mt-4 text-sm text-red-400">{error}</p>}
        <button disabled={busy} className="mt-6 flex w-full items-center justify-center gap-2 rounded-lg bg-violet-600 px-4 py-3 text-sm font-medium text-white hover:bg-violet-500 disabled:opacity-50">{busy && <Loader2 size={16} className="animate-spin"/>}{mode === "login" ? "Sign In" : "Create Account"}</button>
        <button type="button" onClick={() => { setMode(mode === "login" ? "register" : "login"); setError(""); }} className="mt-5 w-full text-sm text-violet-400">{mode === "login" ? "New to ForgeAI? Create an account" : "Already registered? Sign in"}</button>
      </form>
    </main>
  );
}

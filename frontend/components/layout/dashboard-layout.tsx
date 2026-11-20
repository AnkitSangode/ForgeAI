"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import AppSidebar from "./app-sidebar";
import AppHeader from "./app-header";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!localStorage.getItem("forgeai_access_token")) {
      router.replace(`/login?next=${encodeURIComponent(pathname)}`);
      return;
    }
    setReady(true);
  }, [pathname, router]);

  if (!ready) {
    return <div className="flex min-h-screen items-center justify-center bg-[#09090b] text-sm text-zinc-500">Loading ForgeAI...</div>;
  }

  return (
    <div className="min-h-screen bg-[#09090b]">
      <AppSidebar />
      <div className="ml-[250px] min-h-screen">
        <AppHeader />
        <main className="p-8"><div className="mx-auto max-w-[1500px]">{children}</div></main>
      </div>
    </div>
  );
}

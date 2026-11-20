
"use client";

import { Suspense, useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import AppSidebar from "./app-sidebar";
import AppHeader from "./app-header";

function DashboardLayoutContent({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const pathname = usePathname();

  const [ready, setReady] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem("forgeai_access_token");

    if (!token) {
      router.replace(
        `/login?next=${encodeURIComponent(pathname || "/dashboard")}`
      );
      return;
    }

    setReady(true);
  }, [pathname, router]);

  if (!ready) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#09090b] text-sm text-zinc-500">
        Loading ForgeAI...
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#09090b]">
      <AppSidebar />

      <div className="ml-[250px] min-h-screen">
        <AppHeader />

        <main className="p-8">
          <div className="mx-auto max-w-[1500px]">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center bg-[#09090b] text-sm text-zinc-500">
          Loading ForgeAI...
        </div>
      }
    >
      <DashboardLayoutContent>
        {children}
      </DashboardLayoutContent>
    </Suspense>
  );
}

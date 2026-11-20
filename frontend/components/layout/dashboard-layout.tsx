
import AppSidebar from "./app-sidebar";
import AppHeader from "./app-header";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
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

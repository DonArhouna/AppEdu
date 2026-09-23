import { useState, useEffect } from "react";
import { Navbar } from "./Navbar";
import { Sidebar } from "./SidebarNew";
import { OfflineBanner } from "./OfflineBanner";
import { cn } from "@/lib/utils";

interface MainLayoutProps {
  children: React.ReactNode;
}

export const MainLayout = ({ children }: MainLayoutProps) => {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => {
    return localStorage.getItem("sidebar_collapsed") === "true";
  });

  useEffect(() => {
    localStorage.setItem("sidebar_collapsed", String(sidebarCollapsed));
  }, [sidebarCollapsed]);

  const [isMobile, setIsMobile] = useState(() =>
    typeof window !== "undefined" ? window.innerWidth < 768 : false
  );

  useEffect(() => {
    const handleResize = () => {
      setIsMobile(window.innerWidth < 768);
    };
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  const toggleCollapse = () => setSidebarCollapsed((prev) => !prev);

  // Sidebar widths: expanded = 270px, collapsed = 76px
  const SIDEBAR_EXPANDED = 270;
  const SIDEBAR_COLLAPSED = 76;
  const sidebarWidth = isMobile ? 0 : (sidebarCollapsed ? SIDEBAR_COLLAPSED : SIDEBAR_EXPANDED);

  return (
    <div className="min-h-screen bg-background flex overflow-x-clip">
      {/* ── Sidebar ── */}
      <Sidebar
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        isCollapsed={sidebarCollapsed}
        onToggleCollapse={toggleCollapse}
      />

      {/* ── Right Column: Navbar + Content ── */}
      <div
        className="flex flex-col flex-1 min-w-0 transition-all duration-300 ease-in-out"
        style={{ marginLeft: `${sidebarWidth}px` }}
      >
        {/* Navbar */}
        <Navbar
          onMenuClick={() => setSidebarOpen(true)}
          isCollapsed={sidebarCollapsed}
          onToggleCollapse={toggleCollapse}
        />
        <OfflineBanner />

        {/* Page content */}
        <main className="flex-1 p-4 sm:p-5 md:p-6 overflow-x-hidden min-w-0">
          {children}
        </main>
      </div>
    </div>
  );
};

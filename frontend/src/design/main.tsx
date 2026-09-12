import { StrictMode, useState } from "react";
import { createRoot } from "react-dom/client";
import { DashboardLayout } from "./DashboardLayout";
import type { View } from "./DashboardLayout";
import { OverviewMetrics } from "./OverviewMetrics";
import { PerformanceCharts, SmellyFilesTable } from "./Panels";
import { RefactoringActionList } from "./RefactoringActionList";
import "./theme.css";

/**
 * Faqja e dizajnit, e ndarë nga aplikacioni që punon.
 *
 * Çdo shifër këtu është e shpikur, dhe shiriti sipër e thotë. Kjo faqe ekziston
 * për të gjykuar pamjen; nëse ajo miratohet, komponentët lidhen me API-në e
 * vërtetë dhe të dhënat e rreme hiqen (VD-105).
 */
function Design() {
  const [view, setView] = useState<View>("overview");
  return (
    <DashboardLayout view={view} onView={setView}>
      <MockBanner />
      {view === "overview" ? (
        <div className="space-y-4">
          <OverviewMetrics />
          <RefactoringActionList />
          <div className="grid gap-4 xl:grid-cols-2">
            <PerformanceCharts />
            <SmellyFilesTable />
          </div>
        </div>
      ) : (
        <div className="grid gap-4 xl:grid-cols-2">
          <PerformanceCharts />
          <SmellyFilesTable />
        </div>
      )}
    </DashboardLayout>
  );
}

function MockBanner() {
  return (
    <p className="mb-4 rounded-lg border border-medium/30 bg-medium/10 px-3 py-2 text-xs text-medium">
      Pamje dizajni. Çdo shifër këtu është e shpikur dhe nuk vjen nga asnjë analizë.
    </p>
  );
}

createRoot(document.getElementById("root") as HTMLElement).render(
  <StrictMode>
    <Design />
  </StrictMode>,
);

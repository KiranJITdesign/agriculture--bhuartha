import { api } from "../api.js";
import {
  bindTraceCopyHandlers,
  renderEmptyState,
  renderErrorState,
  renderLoadingSkeleton,
} from "../components/AsyncState.js";
import { renderAttentionList } from "../components/AttentionList.js";
import { renderRegionTable } from "../components/RegionTable.js";
import { renderStatCard } from "../components/StatCard.js";

export async function renderDashboardPage(container) {
  container.innerHTML = `
    <div class="page-header">
      <div>
        <h2 class="page-title">Dashboard</h2>
        <p class="page-subtitle">Overview of monitored agricultural regions and recent Sentinel-2 analyses.</p>
      </div>
    </div>
    <div id="dash-body">${renderLoadingSkeleton(5)}</div>
  `;

  const bodyEl = container.querySelector("#dash-body");
  try {
    const [regData, anaData] = await Promise.all([api.getRegions(), api.getAnalyses()]);
    const regions = regData.results || [];
    const analyses = anaData.results || [];

    if (regions.length === 0) {
      bodyEl.innerHTML = renderEmptyState(
        "No agricultural regions registered yet. Draw a field boundary to begin monitoring.",
        "Create region",
        "#/regions"
      );
      return;
    }

    const totalAreaHa = regions.reduce((acc, r) => acc + Number(r.area_ha), 0);
    const latestByRegion = new Map();
    analyses.forEach((a) => {
      if (!latestByRegion.has(a.region)) latestByRegion.set(a.region, a);
    });
    const regionNameById = new Map(regions.map((r) => [r.id, r.name]));
    const totalLowHa = Array.from(latestByRegion.values()).reduce(
      (acc, a) => acc + Number(a.relative_low_area_ha),
      0
    );
    const avgCov = latestByRegion.size
      ? (
          Array.from(latestByRegion.values()).reduce((acc, a) => acc + Number(a.valid_pixel_pct), 0) /
          latestByRegion.size
        ).toFixed(2)
      : "0.00";

    bodyEl.innerHTML = `
      <div class="grid-4">
        ${renderStatCard({ label: "Monitored regions", value: String(regions.length) })}
        ${renderStatCard({ label: "Total boundary area", value: `${totalAreaHa.toFixed(2)} ha` })}
        ${renderStatCard({ label: "Completed analyses", value: String(analyses.length) })}
        ${renderStatCard({ label: "Flagged low greenness", value: `${totalLowHa.toFixed(2)} ha`, meta: `Mean coverage: ${avgCov}%` })}
      </div>
      <div class="dashboard-grid">
        <div class="panel">
          <h3>Regions</h3>
          <div id="dash-region-table"></div>
        </div>
        <div class="panel">
          <h3>Attention list</h3>
          <div id="dash-attention-list"></div>
        </div>
      </div>
    `;
    renderRegionTable(bodyEl.querySelector("#dash-region-table"), regions, latestByRegion);
    renderAttentionList(bodyEl.querySelector("#dash-attention-list"), analyses, regionNameById);
  } catch (err) {
    bodyEl.innerHTML = renderErrorState(err.message, err.traceId, "retry-dash");
    bindTraceCopyHandlers(bodyEl);
    bodyEl.querySelector("#retry-dash")?.addEventListener("click", () => renderDashboardPage(container));
  }
}

import { api } from "../api.js";
import {
  bindTraceCopyHandlers,
  renderEmptyState,
  renderErrorState,
  renderLoadingSkeleton,
} from "../components/AsyncState.js";
import { renderDiffLegend } from "../components/DiffLegend.js";
import { renderStatCard } from "../components/StatCard.js";
import { initSyncedMaps } from "../components/SyncedMaps.js";

export async function renderComparePage(container) {
  container.innerHTML = `
    <div class="page-header">
      <div>
        <h2 class="page-title">Compare Periods</h2>
        <p class="page-subtitle">Two-period Delta NDVI comparison binned at +/-0.05 across analysed cropland.</p>
      </div>
    </div>
    <form id="compare-form" class="panel weather-controls">
      <div>
        <label class="field-label" for="cmp-region">Region</label>
        <select id="cmp-region" class="select" required></select>
      </div>
      <div>
        <label class="field-label" for="cmp-a1">Period A start</label>
        <input id="cmp-a1" class="input" type="date" required>
      </div>
      <div>
        <label class="field-label" for="cmp-a2">Period A end</label>
        <input id="cmp-a2" class="input" type="date" required>
      </div>
      <div>
        <label class="field-label" for="cmp-b1">Period B start</label>
        <input id="cmp-b1" class="input" type="date" required>
      </div>
      <div>
        <label class="field-label" for="cmp-b2">Period B end</label>
        <input id="cmp-b2" class="input" type="date" required>
      </div>
      <button class="btn btn-primary" type="submit">Compare</button>
    </form>
    <div id="cmp-content"></div>
  `;

  const regSel = container.querySelector("#cmp-region");
  const contentEl = container.querySelector("#cmp-content");
  let regions = [];

  try {
    const data = await api.getRegions();
    regions = data.results || [];
    if (regions.length === 0) {
      contentEl.innerHTML = renderEmptyState("No saved regions found.", "Go to Regions", "#/regions");
      return;
    }
    regSel.innerHTML = regions.map((r) => `<option value="${r.id}">${r.name}</option>`).join("");
  } catch (err) {
    contentEl.innerHTML = renderErrorState(err.message, err.traceId, "retry-cmp-reg");
    bindTraceCopyHandlers(contentEl);
    return;
  }

  container.querySelector("#compare-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const regionObj = regions.find((r) => r.id === regSel.value);
    contentEl.innerHTML = renderLoadingSkeleton(4);
    try {
      const payload = {
        region: regSel.value,
        period_a_start: container.querySelector("#cmp-a1").value,
        period_a_end: container.querySelector("#cmp-a2").value,
        period_b_start: container.querySelector("#cmp-b1").value,
        period_b_end: container.querySelector("#cmp-b2").value,
      };
      const res = await api.comparePeriods(payload);

      contentEl.innerHTML = `
        <div class="grid-3" style="margin-bottom:var(--s-4);align-items:center">
          ${renderStatCard({ label: "Mean Delta NDVI", value: res.mean_delta_ndvi })}
          ${renderStatCard({ label: "Analysed cropland area", value: `${res.analysed_area_ha} ha` })}
          <div class="stat-card" style="display:flex;justify-content:space-between;align-items:center;gap:8px">
            <div>
              <p class="stat-label">Comparison Report</p>
              <p class="stat-meta">Includes Period A/B &amp; Delta NDVI map</p>
            </div>
            <button id="cmp-download-pdf" class="btn btn-primary" type="button">Download PDF</button>
          </div>
        </div>
        <div class="compare-maps-grid">
          <div class="panel"><h3>Period A</h3><div id="cmp-map-a" class="compare-map"></div></div>
          <div class="panel"><h3>Period B</h3><div id="cmp-map-b" class="compare-map"></div></div>
          <div class="panel"><h3>Delta NDVI</h3><div id="cmp-map-diff" class="compare-map"></div><div id="diff-legend-host"></div></div>
        </div>
      `;
      initSyncedMaps(["cmp-map-a", "cmp-map-b", "cmp-map-diff"], regionObj.boundary, res.tiles?.diff_url);
      renderDiffLegend(contentEl.querySelector("#diff-legend-host"));
      contentEl.querySelector("#cmp-download-pdf").addEventListener("click", () => {
        api.downloadCompareReportPdf({
          ...payload,
          mean_delta_ndvi: res.mean_delta_ndvi,
          analysed_area_ha: res.analysed_area_ha,
          bins: res.bins || [],
          diff_tile_url: res.tiles?.diff_url || "",
        });
      });
    } catch (err) {
      contentEl.innerHTML = renderErrorState(err.message, err.traceId, "retry-cmp");
      bindTraceCopyHandlers(contentEl);
    }
  });
}

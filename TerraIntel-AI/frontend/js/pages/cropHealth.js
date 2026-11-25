import { api } from "../api.js";
import {
  bindTraceCopyHandlers,
  renderCoverageBanner,
  renderEmptyState,
  renderErrorState,
  renderLoadingSkeleton,
} from "../components/AsyncState.js";
import { renderNdviHistogram } from "../components/NdviHistogram.js";
import { renderNdviLegend } from "../components/NdviLegend.js";
import { initNdviMap } from "../components/NdviMap.js";
import { renderStatCard } from "../components/StatCard.js";

export async function renderCropHealthPage(container) {
  container.innerHTML = `
    <div class="workbench-3col">
      <div class="pane-scroll">
        <div class="panel">
          <h3>Analysis Parameters</h3>
          <form id="analysis-form" class="region-form">
            <div>
              <label class="field-label" for="ch-region">Region</label>
              <select id="ch-region" class="select" required></select>
            </div>
            <div>
              <label class="field-label" for="ch-start">Start date</label>
              <input id="ch-start" class="input" type="date" required>
            </div>
            <div>
              <label class="field-label" for="ch-end">End date</label>
              <input id="ch-end" class="input" type="date" required>
            </div>
            <button class="btn btn-primary" type="submit">Run Sentinel-2 analysis</button>
          </form>
        </div>
        <div id="ch-status"></div>
        <div id="ch-provenance" class="panel">
          <h3>Scene Provenance</h3>
          <p class="stat-meta">Select a region and run analysis to inspect Sentinel-2 scenes.</p>
        </div>
      </div>

      <div id="ch-map-pane" class="panel ndvi-map-wrap">
        <div class="map-toolbar">
          <button type="button" class="btn" id="layer-ndvi">NDVI</button>
          <button type="button" class="btn" id="layer-tc">True colour</button>
        </div>
        <div id="ndvi-map" class="map-canvas"></div>
        <div id="ndvi-legend-host"></div>
      </div>

      <div id="ch-ledger-pane" class="pane-scroll"></div>
    </div>
  `;

  const regionSel = container.querySelector("#ch-region");
  const statusEl = container.querySelector("#ch-status");
  const provEl = container.querySelector("#ch-provenance");
  const ledgerEl = container.querySelector("#ch-ledger-pane");

  let regions = [];
  let mapCtrl = null;

  try {
    const regData = await api.getRegions();
    regions = regData.results || [];
    if (regions.length === 0) {
      ledgerEl.innerHTML = renderEmptyState(
        "No saved regions found. Create an agricultural boundary first.",
        "Go to Regions",
        "#/regions"
      );
      return;
    }
    regionSel.innerHTML = regions
      .map((r) => `<option value="${r.id}">${r.name} (${r.area_ha} ha)</option>`)
      .join("");
  } catch (err) {
    ledgerEl.innerHTML = renderErrorState(err.message, err.traceId, "retry-ch-regions");
    bindTraceCopyHandlers(ledgerEl);
    return;
  }

  function renderAnalysisResult(analysis, regionObj) {
    const coverageBanner = analysis.low_coverage
      ? renderCoverageBanner(analysis.valid_pixel_pct)
      : "";
    const scenesHtml = (analysis.scenes || [])
      .slice(0, 5)
      .map(
        (s) =>
          `<div class="panel-sunken" style="margin-bottom:6px"><div class="mono">${s.scene_id}</div><div class="stat-meta">${s.acquired_at}</div></div>`
      )
      .join("");
    provEl.innerHTML = `<h3>Scene Provenance</h3>${scenesHtml || '<p class="stat-meta">No scene metadata.</p>'}`;

    const classRows = (analysis.class_stats || [])
      .map(
        (cs) => `
      <tr>
        <td>${cs.vigour_class}</td>
        <td class="mono">${cs.area_ha} ha</td>
        <td class="mono">${cs.area_pct}%</td>
      </tr>`
      )
      .join("");

    ledgerEl.innerHTML = `
      ${coverageBanner}
      <div class="panel">
        <div class="ledger-header">
          <div>
            <h3>Crop Health Ledger</h3>
            <span class="stat-meta">Valid coverage: ${analysis.valid_pixel_pct}% | Anomalous: ${analysis.anomalous_pixel_pct}%</span>
          </div>
          <div style="display:flex;gap:6px">
            <a class="btn" href="${api.getLowVigourGeoJsonUrl(analysis.id)}">GeoJSON</a>
            <a class="btn btn-primary" href="${api.getReportPdfUrl(analysis.id)}">PDF</a>
          </div>
        </div>
        <div class="grid-3" style="margin-bottom:var(--s-3)">
          ${renderStatCard({ label: "Mean NDVI", value: analysis.mean_ndvi, meta: `Cov: ${analysis.valid_pixel_pct}%` })}
          ${renderStatCard({ label: "Cropland", value: `${analysis.cropland_area_ha} ha`, meta: `Valid: ${analysis.valid_area_ha} ha` })}
          ${renderStatCard({ label: "Low Greenness", value: `${analysis.relative_low_area_ha} ha`, meta: `Abs: ${analysis.absolute_low_area_ha} ha` })}
        </div>
        <table class="data-table" style="margin-bottom:var(--s-3)">
          <thead><tr><th>Vigour Class</th><th>Area</th><th>Share</th></tr></thead>
          <tbody>${classRows}</tbody>
        </table>
        <h3>Vigour Distribution</h3>
        <div class="chart-box"><canvas id="ndvi-hist-canvas"></canvas></div>
      </div>
    `;

    if (mapCtrl && mapCtrl.map) mapCtrl.map.remove();
    mapCtrl = initNdviMap("ndvi-map", regionObj.boundary, analysis.tiles, analysis.id);
    renderNdviLegend(container.querySelector("#ndvi-legend-host"));
    container.querySelector("#layer-ndvi").onclick = () => mapCtrl.setLayer("ndvi");
    container.querySelector("#layer-tc").onclick = () => mapCtrl.setLayer("true_colour");
    renderNdviHistogram(ledgerEl.querySelector("#ndvi-hist-canvas"), analysis.class_stats || []);
  }

  async function loadLatestForRegion(regionId) {
    const regionObj = regions.find((r) => r.id === regionId);
    if (!regionObj) return;
    if (mapCtrl && mapCtrl.map) mapCtrl.map.remove();
    mapCtrl = initNdviMap("ndvi-map", regionObj.boundary, null);
    renderNdviLegend(container.querySelector("#ndvi-legend-host"));
    try {
      const list = await api.getAnalyses();
      const match = (list.results || []).find((a) => a.region === regionId);
      if (match) {
        statusEl.innerHTML = "";
        renderAnalysisResult(match, regionObj);
      } else {
        ledgerEl.innerHTML = renderEmptyState("No saved analysis for this region yet. Pick a date range and run analysis.");
      }
    } catch (err) {
      ledgerEl.innerHTML = renderErrorState(err.message, err.traceId, "retry-load-analysis");
      bindTraceCopyHandlers(ledgerEl);
    }
  }

  regionSel.addEventListener("change", () => loadLatestForRegion(regionSel.value));
  await loadLatestForRegion(regionSel.value);

  container.querySelector("#analysis-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const regionId = regionSel.value;
    const regionObj = regions.find((r) => r.id === regionId);
    statusEl.innerHTML = renderLoadingSkeleton(3);
    try {
      const resp = await api.submitJob({
        region: regionId,
        start_date: container.querySelector("#ch-start").value,
        end_date: container.querySelector("#ch-end").value,
      });
      if (resp.cached && resp.analysis) {
        statusEl.innerHTML = "";
        renderAnalysisResult(resp.analysis, regionObj);
        return;
      }
      const jobId = resp.id;
      const pollTimer = setInterval(async () => {
        try {
          const job = await api.getJob(jobId);
          if (job.status === "SUCCEEDED") {
            clearInterval(pollTimer);
            statusEl.innerHTML = "";
            const list = await api.getAnalyses();
            const match = (list.results || []).find((a) => a.job === jobId);
            if (match) renderAnalysisResult(match, regionObj);
          } else if (job.status === "FAILED") {
            clearInterval(pollTimer);
            statusEl.innerHTML = renderErrorState(
              `${job.failure_code}: ${job.failure_detail}`,
              job.trace_id,
              "retry-job-btn"
            );
            bindTraceCopyHandlers(statusEl);
          }
        } catch (err) {
          clearInterval(pollTimer);
          statusEl.innerHTML = renderErrorState(err.message, err.traceId, "retry-job-btn");
          bindTraceCopyHandlers(statusEl);
        }
      }, 2000);
    } catch (err) {
      statusEl.innerHTML = renderErrorState(err.message, err.traceId, "retry-submit-btn");
      bindTraceCopyHandlers(statusEl);
    }
  });
}

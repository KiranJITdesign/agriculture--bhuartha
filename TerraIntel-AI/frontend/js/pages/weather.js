import { api } from "../api.js";
import {
  bindTraceCopyHandlers,
  renderEmptyState,
  renderErrorState,
  renderLoadingSkeleton,
} from "../components/AsyncState.js";
import { renderStatCard } from "../components/StatCard.js";
import { renderWeatherChart } from "../components/WeatherChart.js";

function downloadCsv(filename, daily) {
  const header = "date,rainfall_mm,temperature_c\n";
  const rows = daily.map((d) => `${d.date},${d.rainfall_mm},${d.temperature_c}`).join("\n");
  const blob = new Blob([header + rows], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export async function renderWeatherPage(container) {
  container.innerHTML = `
    <div class="page-header">
      <div>
        <h2 class="page-title">Weather</h2>
        <p class="page-subtitle">NASA POWER daily rainfall (mm) and 2m temperature (C) with 5-year rainfall anomaly.</p>
      </div>
    </div>
    <form id="weather-form" class="panel weather-controls">
      <div>
        <label class="field-label" for="w-region">Region</label>
        <select id="w-region" class="select" required></select>
      </div>
      <div>
        <label class="field-label" for="w-start">Start date</label>
        <input id="w-start" class="input" type="date" required>
      </div>
      <div>
        <label class="field-label" for="w-end">End date</label>
        <input id="w-end" class="input" type="date" required>
      </div>
      <button class="btn btn-primary" type="submit">Load weather</button>
    </form>
    <div id="w-content"></div>
  `;

  const regSel = container.querySelector("#w-region");
  const contentEl = container.querySelector("#w-content");

  try {
    const data = await api.getRegions();
    const regions = data.results || [];
    if (regions.length === 0) {
      contentEl.innerHTML = renderEmptyState("No saved regions found.", "Go to Regions", "#/regions");
      return;
    }
    regSel.innerHTML = regions.map((r) => `<option value="${r.id}">${r.name}</option>`).join("");
  } catch (err) {
    contentEl.innerHTML = renderErrorState(err.message, err.traceId, "retry-w-reg");
    bindTraceCopyHandlers(contentEl);
    return;
  }

  container.querySelector("#weather-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    contentEl.innerHTML = renderLoadingSkeleton(4);
    try {
      const w = await api.getWeather(
        regSel.value,
        container.querySelector("#w-start").value,
        container.querySelector("#w-end").value
      );
      const anomalyDisplay = w.anomaly_pct !== null ? `${w.anomaly_pct}%` : "N/A";
      const anomalyMeta = w.anomaly_reason || `5-year baseline: ${w.baseline_rainfall_mm} mm`;

      contentEl.innerHTML = `
        <div class="grid-4" style="margin-bottom:var(--s-4)">
          ${renderStatCard({ label: "Total rainfall", value: `${w.total_rainfall_mm} mm` })}
          ${renderStatCard({ label: "Mean temperature", value: `${w.mean_temperature_c} C` })}
          ${renderStatCard({ label: "5-year baseline rain", value: `${w.baseline_rainfall_mm} mm` })}
          ${renderStatCard({ label: "Rainfall anomaly", value: anomalyDisplay, meta: anomalyMeta })}
        </div>
        <div class="panel">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:var(--s-3)">
            <h3>Daily series (${w.start_date} to ${w.end_date})</h3>
            <button id="export-weather-csv" class="btn" type="button">Export CSV</button>
          </div>
          <div class="weather-chart-box"><canvas id="weather-canvas"></canvas></div>
        </div>
      `;
      renderWeatherChart(contentEl.querySelector("#weather-canvas"), w.daily || []);
      contentEl.querySelector("#export-weather-csv").addEventListener("click", () => {
        downloadCsv(`weather-${w.region}-${w.start_date}.csv`, w.daily || []);
      });
    } catch (err) {
      contentEl.innerHTML = renderErrorState(err.message, err.traceId, "retry-weather");
      bindTraceCopyHandlers(contentEl);
    }
  });
}

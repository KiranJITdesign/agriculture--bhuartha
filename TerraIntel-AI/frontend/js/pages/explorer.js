import { api, apiRequest } from "../api.js";
import {
  bindTraceCopyHandlers,
  renderCoverageBanner,
  renderEmptyState,
  renderErrorState,
  renderLoadingSkeleton,
} from "../components/AsyncState.js";
import { renderNdviHistogram } from "../components/NdviHistogram.js";
import { renderNdviLegend } from "../components/NdviLegend.js";
import { renderStatCard } from "../components/StatCard.js";

const CITIES = [
  { label: "Bengaluru (Karnataka)", crop: "Ragi", crops: ["Ragi", "Maize", "Paddy", "Tomato", "Chilli"], lat: 13.285, lon: 77.745 },
  { label: "Mumbai (Maharashtra)", crop: "Paddy", crops: ["Paddy", "Finger Millet", "Pulses", "Vegetables"], lat: 19.705, lon: 72.865 },
  { label: "Chennai (Tamil Nadu)", crop: "Paddy", crops: ["Paddy", "Groundnut", "Sugarcane", "Chilli", "Pulses"], lat: 13.145, lon: 79.905 },
  { label: "Hyderabad (Telangana)", crop: "Paddy", crops: ["Paddy", "Cotton", "Chilli", "Maize", "Red Gram"], lat: 17.565, lon: 78.845 },
  { label: "Delhi (Delhi NCR)", crop: "Wheat", crops: ["Wheat", "Paddy", "Mustard", "Sugarcane", "Vegetables"], lat: 28.865, lon: 77.085 },
  { label: "Pune (Maharashtra)", crop: "Sugarcane", crops: ["Sugarcane", "Jowar", "Bajra", "Onion", "Soybean"], lat: 18.155, lon: 74.575 },
  { label: "Kolkata (West Bengal)", crop: "Paddy", crops: ["Paddy", "Jute", "Potato", "Mustard", "Vegetables"], lat: 22.845, lon: 88.455 },
];

function bboxPolygon(lat, lon, delta = 0.012) {
  return {
    type: "Polygon",
    coordinates: [
      [
        [lon - delta, lat - delta],
        [lon + delta, lat - delta],
        [lon + delta, lat + delta],
        [lon - delta, lat + delta],
        [lon - delta, lat - delta],
      ],
    ],
  };
}

function isoDaysAgo(days) {
  const d = new Date();
  d.setUTCDate(d.getUTCDate() - days);
  return d.toISOString().slice(0, 10);
}

function resolveMediaUrl(url) {
  if (!url) return "";
  if (url.startsWith("http")) return url;
  return `${window.location.protocol}//${window.location.hostname || "127.0.0.1"}:8010${url}`;
}

function ringAreaHa(latLngs) {
  if (window.L && L.GeometryUtil && latLngs && latLngs.length >= 3) {
    return L.GeometryUtil.geodesicArea(latLngs) / 10000;
  }
  return 0;
}

function downloadSummaryCsv(analysis, weather, regionName) {
  const lines = [
    "metric,value,unit",
    `region,${regionName},name`,
    `window,${analysis.start_date} to ${analysis.end_date},date_range`,
    `mean_ndvi,${analysis.mean_ndvi},unitless`,
    `p50_ndvi,${analysis.p50_ndvi},unitless`,
    `cropland_area_ha,${analysis.cropland_area_ha},ha`,
    `valid_area_ha,${analysis.valid_area_ha},ha`,
    `valid_pixel_pct,${analysis.valid_pixel_pct},pct`,
    `absolute_low_area_ha,${analysis.absolute_low_area_ha},ha`,
    `relative_low_area_ha,${analysis.relative_low_area_ha},ha`,
  ];
  if (weather) {
    lines.push(`total_rainfall_mm,${weather.total_rainfall_mm},mm`);
    lines.push(`mean_temperature_c,${weather.mean_temperature_c},C`);
  }
  const blob = new Blob([lines.join("\n")], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `crop-health-${analysis.id}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

export async function renderExplorerPage(container) {
  const cityOptions = CITIES.map(
    (c, idx) => `<option value="city:${idx}" ${c.label.startsWith("Delhi") ? "selected" : ""}>${c.label}</option>`
  ).join("");

  container.innerHTML = `
    <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:8px">
      <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">
        <select id="exp-city-sel" class="select" style="width:210px" aria-label="Select city">
          ${cityOptions}
        </select>
        <select id="exp-crop-sel" class="select" style="width:140px" aria-label="Select crop type"></select>
        <select id="exp-window-sel" class="select" style="width:120px" aria-label="Select observation window">
          <option value="30" selected>1 Month</option>
          <option value="90">3 Months</option>
          <option value="180">6 Months</option>
          <option value="365">12 Months</option>
        </select>
        <button id="exp-analyze-btn" class="btn btn-primary" type="button">Analyze</button>
        <button id="exp-near-me-btn" class="btn" type="button">Near Me</button>
      </div>
      <div id="exp-area-pill" class="status-pill mono">Selected Area: Delhi (Delhi NCR)</div>
    </div>

    <div class="workbench-3col" style="height:calc(100vh - 118px)">
      <div class="pane-scroll">
        <div class="panel">
          <div class="ledger-header">
            <h3>Agronomic AI Copilot</h3>
            <button type="button" id="exp-clear-feed" class="btn">Clear</button>
          </div>
          <div id="exp-copilot-feed" class="region-form"></div>
          <div id="exp-job-status" style="margin-top:8px"></div>
        </div>

        <div class="panel">
          <div class="chip-row" style="margin-bottom:8px">
            <button type="button" class="chip-btn" data-prompt="Summarize crop health and NDVI condition">Summarize crop health</button>
            <button type="button" class="chip-btn" data-prompt="Inspect detected low-greenness problem zones">Inspect problem zones</button>
            <button type="button" class="chip-btn" data-prompt="Analyze rainfall and temperature impact">Rainfall &amp; temp</button>
          </div>
          <form id="exp-ask-form" class="search-row" style="margin-bottom:0">
            <input id="exp-ask-input" class="input" type="text" placeholder="Ask OpenAI Agronomic Copilot...">
            <button class="btn btn-primary" type="submit">Send</button>
          </form>
        </div>
      </div>

      <div class="panel ndvi-map-wrap">
        <div class="map-toolbar">
          <button type="button" class="btn" id="exp-draw-roi">Draw ROI</button>
          <button type="button" class="btn" id="exp-clear-roi">Clear</button>
          <button type="button" class="btn btn-primary" id="exp-layer-ndvi">NDVI</button>
          <button type="button" class="btn" id="exp-layer-tc">True colour</button>
        </div>
        <div id="exp-map" class="map-canvas" aria-label="Copernicus Sentinel-2 Interactive Map"></div>
        <div id="exp-legend-host"></div>
      </div>

      <div id="exp-right-pane" class="pane-scroll"></div>
    </div>
  `;

  const citySel = container.querySelector("#exp-city-sel");
  const cropSel = container.querySelector("#exp-crop-sel");
  const windowSel = container.querySelector("#exp-window-sel");
  const areaPill = container.querySelector("#exp-area-pill");
  const statusEl = container.querySelector("#exp-job-status");
  const feedEl = container.querySelector("#exp-copilot-feed");
  const rightEl = container.querySelector("#exp-right-pane");

  const map = L.map("exp-map").setView([28.865, 77.085], 13);
  const esriSat = L.tileLayer(
    "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    { attribution: "Tiles &copy; Esri World Imagery", maxZoom: 19 }
  );
  const s2Sat = L.tileLayer(
    "https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless-2021_3857/default/g/{z}/{y}/{x}.jpg",
    { attribution: "Sentinel-2 cloudless by EOX (CC-BY 4.0)", maxZoom: 18 }
  );
  const street = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "&copy; OpenStreetMap contributors",
    maxZoom: 19,
  });
  const labels = L.tileLayer(
    "https://tiles.maps.eox.at/wmts/1.0.0/overlay_3857/default/g/{z}/{y}/{x}.png",
    { attribution: "Overlay by EOX / OpenStreetMap contributors", maxZoom: 18 }
  );
  esriSat.addTo(map);
  labels.addTo(map);
  L.control
    .layers(
      {
        "Satellite (High-Res)": esriSat,
        "Satellite (Sentinel-2)": s2Sat,
        "Street (OSM)": street,
      },
      { "Place & road labels": labels }
    )
    .addTo(map);

  const drawnItems = new L.FeatureGroup();
  const overlayGroup = new L.LayerGroup();
  map.addLayer(drawnItems);
  map.addLayer(overlayGroup);

  const drawControl = new L.Control.Draw({
    edit: { featureGroup: drawnItems },
    draw: {
      polygon: { allowIntersection: false, showArea: true },
      rectangle: true,
      polyline: false,
      circle: false,
      circlemarker: false,
      marker: false,
    },
  });
  map.addControl(drawControl);
  renderNdviLegend(container.querySelector("#exp-legend-host"));

  let drawnGeometry = null;
  let activeBounds = null;
  let activeOverlayLayer = null;
  let activeTiles = null;
  let currentAnalysis = null;
  let currentWeather = null;
  let currentRegion = null;
  let currentZones = [];
  let savedRegions = [];

  function appendFeedCard(title, body) {
    const card = document.createElement("div");
    card.className = "copilot-card";
    card.innerHTML = `<p class="copilot-card-title">${title}</p><div>${body}</div>`;
    feedEl.appendChild(card);
    feedEl.scrollTop = feedEl.scrollHeight;
  }

  container.querySelector("#exp-clear-feed").addEventListener("click", () => {
    feedEl.innerHTML = "";
  });

  container.querySelector("#exp-draw-roi").addEventListener("click", () => {
    new L.Draw.Polygon(map, drawControl.options.draw.polygon).enable();
  });

  container.querySelector("#exp-clear-roi").addEventListener("click", () => {
    drawnGeometry = null;
    drawnItems.clearLayers();
    overlayGroup.clearLayers();
    areaPill.textContent = "Selected Area: 0.00 ha";
  });

  map.on(L.Draw.Event.CREATED, (e) => {
    drawnItems.clearLayers();
    overlayGroup.clearLayers();
    drawnItems.addLayer(e.layer);
    drawnGeometry = e.layer.toGeoJSON().geometry;
    activeBounds = e.layer.getBounds();
    const ha = ringAreaHa(e.layer.getLatLngs()[0] || []);
    areaPill.textContent = `Drawn ROI: ${ha.toFixed(2)} ha`;
    appendFeedCard("ROI Drawn", `New plot (${ha.toFixed(2)} ha) ready. Click Analyze.`);
  });

  function setMapOverlay(mode) {
    if (activeOverlayLayer) {
      overlayGroup.removeLayer(activeOverlayLayer);
      activeOverlayLayer = null;
    }
    if (!activeTiles || !activeBounds) return;
    if (!activeTiles.expires_at || Date.now() > Date.parse(activeTiles.expires_at)) return;
    const rawUrl = mode === "tc" ? activeTiles.true_colour_url : activeTiles.ndvi_url;
    if (!rawUrl) return;
    const url = resolveMediaUrl(rawUrl);
    if (url.includes("{z}")) {
      activeOverlayLayer = L.tileLayer(url, { opacity: 0.85 }).addTo(overlayGroup);
    } else {
      activeOverlayLayer = L.imageOverlay(url, activeBounds, { opacity: 0.85 }).addTo(overlayGroup);
    }
  }

  container.querySelector("#exp-layer-ndvi").addEventListener("click", () => setMapOverlay("ndvi"));
  container.querySelector("#exp-layer-tc").addEventListener("click", () => setMapOverlay("tc"));

  function buildCopilotContext(analysis, weather, regionObj, lowZones) {
    return {
      region_name: regionObj.name,
      start_date: analysis.start_date,
      end_date: analysis.end_date,
      mean_ndvi: analysis.mean_ndvi,
      p25_ndvi: analysis.p25_ndvi,
      p50_ndvi: analysis.p50_ndvi,
      p75_ndvi: analysis.p75_ndvi,
      cropland_area_ha: analysis.cropland_area_ha,
      valid_area_ha: analysis.valid_area_ha,
      valid_pixel_pct: analysis.valid_pixel_pct,
      absolute_low_area_ha: analysis.absolute_low_area_ha,
      relative_low_area_ha: analysis.relative_low_area_ha,
      problem_zone_count: lowZones.length,
      class_stats: analysis.class_stats || [],
      total_rainfall_mm: weather ? weather.total_rainfall_mm : "N/A",
      mean_temperature_c: weather ? weather.mean_temperature_c : "N/A",
      anomaly_pct: weather ? weather.anomaly_pct : null,
      anomaly_reason: weather ? weather.anomaly_reason : null,
    };
  }

  function renderRightPanel(analysis, weather, regionObj, lowZones, aiSummary) {
    const covBanner = analysis.low_coverage ? renderCoverageBanner(analysis.valid_pixel_pct) : "";
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

    const zoneRows = lowZones
      .slice(0, 8)
      .map(
        (z, i) => `
      <tr>
        <td class="mono">#${i + 1}</td>
        <td>${z.properties.zone_type || "RELATIVE"}</td>
        <td class="mono">${z.properties.area_ha} ha</td>
        <td class="mono">${z.properties.valid_pixel_pct}%</td>
      </tr>`
      )
      .join("");

    const rainText = weather ? `${weather.total_rainfall_mm} mm` : "N/A";
    const tempText = weather ? `${weather.mean_temperature_c} C` : "N/A";

    rightEl.innerHTML = `
      ${covBanner}
      <div class="panel">
        <div class="ledger-header">
          <div>
            <h3>Crop Health Ledger</h3>
            <span class="stat-meta">${regionObj.name} | Coverage: ${analysis.valid_pixel_pct}%</span>
          </div>
          <div style="display:flex;gap:6px">
            <button type="button" id="exp-csv-btn" class="btn">CSV</button>
            <a class="btn" href="${api.getLowVigourGeoJsonUrl(analysis.id)}">GeoJSON</a>
          </div>
        </div>

        <div class="grid-3" style="margin-bottom:var(--s-3)">
          ${renderStatCard({ label: "Mean NDVI", value: analysis.mean_ndvi, meta: `p50: ${analysis.p50_ndvi}` })}
          ${renderStatCard({ label: "Cropland", value: `${analysis.cropland_area_ha} ha`, meta: `Cov: ${analysis.valid_pixel_pct}%` })}
          ${renderStatCard({ label: "Rain / Temp", value: rainText, meta: `Mean: ${tempText}` })}
        </div>

        <div class="copilot-card" style="margin-bottom:var(--s-3)">
          <p class="copilot-card-title">OpenAI Insights (${aiSummary.provider})</p>
          <p style="margin:0">${aiSummary.answer}</p>
        </div>

        <h3>Vegetation Health Classification</h3>
        <table class="data-table" style="margin-bottom:var(--s-3)">
          <thead><tr><th>Class</th><th>Area</th><th>Share</th></tr></thead>
          <tbody>${classRows}</tbody>
        </table>

        <h3>Detected Problem Areas (${lowZones.length})</h3>
        ${
          zoneRows
            ? `<table class="data-table" style="margin-bottom:var(--s-3)">
                <thead><tr><th>Zone</th><th>Type</th><th>Area</th><th>Cov</th></tr></thead>
                <tbody>${zoneRows}</tbody>
              </table>`
            : `<p class="stat-meta" style="margin-bottom:var(--s-3)">No localized low-greenness polygons flagged (coverage ${analysis.valid_pixel_pct}%).</p>`
        }

        <h3>Vegetation Class Distribution</h3>
        <div class="chart-box"><canvas id="exp-chart-canvas"></canvas></div>

        <div class="report-box">
          <div class="ledger-header" style="margin-bottom:4px">
            <h3>Downloadable Analysis Report</h3>
            <span class="mono stat-meta">${(analysis.scenes || []).length} S2 scenes</span>
          </div>
          <p class="stat-meta" style="margin:0 0 8px 0">
            Includes Copernicus Sentinel-2 scene IDs, acquisition dates, NDVI thresholds, and coverage provenance.
          </p>
          <div style="display:flex;gap:8px;flex-wrap:wrap">
            <a class="btn btn-primary" href="${api.getReportPdfUrl(analysis.id)}">Download PDF Report</a>
            <a class="btn" href="${api.getLowVigourGeoJsonUrl(analysis.id)}">Download GeoJSON</a>
            <button type="button" id="exp-dl-csv-bottom" class="btn">Download CSV</button>
          </div>
        </div>
      </div>
    `;

    renderNdviHistogram(rightEl.querySelector("#exp-chart-canvas"), analysis.class_stats || []);
    rightEl.querySelector("#exp-csv-btn").onclick = () =>
      downloadSummaryCsv(analysis, weather, regionObj.name);
    rightEl.querySelector("#exp-dl-csv-bottom").onclick = () =>
      downloadSummaryCsv(analysis, weather, regionObj.name);
  }

  async function displayAnalysisOnWorkbench(analysis, regionObj) {
    currentAnalysis = analysis;
    currentRegion = regionObj;
    activeTiles = analysis.tiles;

    drawnItems.clearLayers();
    overlayGroup.clearLayers();
    const boundaryLayer = L.geoJSON(regionObj.boundary, {
      style: { color: "#10B981", weight: 2, fillColor: "#10B981", fillOpacity: 0.08 },
    }).addTo(drawnItems);
    activeBounds = boundaryLayer.getBounds();
    map.fitBounds(activeBounds, { padding: [24, 24] });
    areaPill.textContent = `${regionObj.name} (${regionObj.area_ha} ha)`;

    setMapOverlay("ndvi");

    let lowZones = [];
    try {
      const gz = await apiRequest(api.getLowVigourGeoJsonUrl(analysis.id));
      lowZones = gz?.features || [];
      if (lowZones.length > 0) {
        L.geoJSON(gz, {
          style: { color: "#F59E0B", weight: 2, fillColor: "#EF4444", fillOpacity: 0.35 },
        }).addTo(overlayGroup);
      }
    } catch {
      lowZones = [];
    }
    currentZones = lowZones;

    let weather = null;
    try {
      weather = await api.getWeather(regionObj.id, analysis.start_date, analysis.end_date);
    } catch {
      weather = null;
    }
    currentWeather = weather;

    const ctx = buildCopilotContext(analysis, weather, regionObj, lowZones);
    let aiSummary = { answer: "", provider: "deterministic" };
    try {
      aiSummary = await api.askCopilot(
        "Summarize crop health, NDVI condition, rainfall/temperature impact, and any low-greenness zones.",
        ctx
      );
    } catch {
      aiSummary = {
        answer: `Mean NDVI ${analysis.mean_ndvi} across ${analysis.cropland_area_ha} ha cropland (${analysis.valid_pixel_pct}% coverage).`,
        provider: "deterministic",
      };
    }

    feedEl.innerHTML = "";
    appendFeedCard(
      "Copernicus Sentinel-2 L2A Live",
      `<strong>${regionObj.name}</strong> (${analysis.start_date} to ${analysis.end_date}): Mean NDVI <strong>${analysis.mean_ndvi}</strong>, Cropland <strong>${analysis.cropland_area_ha} ha</strong> (${analysis.valid_pixel_pct}% coverage).`
    );
    appendFeedCard(`Agronomic Copilot (${aiSummary.provider})`, aiSummary.answer);

    renderRightPanel(analysis, weather, regionObj, lowZones, aiSummary);
  }

  async function runAnalysisForRegion(regionId) {
    statusEl.innerHTML = renderLoadingSkeleton(2);
    const days = Number(windowSel.value || 30);
    const startDate = isoDaysAgo(days);
    const endDate = isoDaysAgo(0);
    try {
      const resp = await api.submitJob({ region: regionId, start_date: startDate, end_date: endDate });
      if (resp.cached && resp.analysis) {
        statusEl.innerHTML = "";
        const [regData, anaData] = await Promise.all([api.getRegions(), api.getAnalyses()]);
        savedRegions = regData.results || [];
        const reg = savedRegions.find((r) => r.id === regionId);
        if (reg) await displayAnalysisOnWorkbench(resp.analysis, reg);
        return;
      }
      const jobId = resp.id;
      const timer = setInterval(async () => {
        try {
          const job = await api.getJob(jobId);
          if (job.status === "SUCCEEDED") {
            clearInterval(timer);
            statusEl.innerHTML = "";
            const [regData, anaData] = await Promise.all([api.getRegions(), api.getAnalyses()]);
            savedRegions = regData.results || [];
            const reg = savedRegions.find((r) => r.id === regionId);
            const match = (anaData.results || []).find((a) => a.job === jobId);
            if (reg && match) await displayAnalysisOnWorkbench(match, reg);
          } else if (job.status === "FAILED") {
            clearInterval(timer);
            statusEl.innerHTML = renderErrorState(
              `${job.failure_code}: ${job.failure_detail}`,
              job.trace_id,
              "retry-exp-job"
            );
            bindTraceCopyHandlers(statusEl);
          }
        } catch (err) {
          clearInterval(timer);
          statusEl.innerHTML = renderErrorState(err.message, err.traceId, "retry-exp-poll");
          bindTraceCopyHandlers(statusEl);
        }
      }, 2000);
    } catch (err) {
      statusEl.innerHTML = renderErrorState(err.message, err.traceId, "retry-exp-submit");
      bindTraceCopyHandlers(statusEl);
    }
  }

  async function selectCityAndFocus(cityIdx) {
    const city = CITIES[cityIdx];
    if (!city) return;
    cropSel.innerHTML = city.crops.map((c) => `<option value="${c}">${c}</option>`).join("");
    drawnGeometry = null;
    drawnItems.clearLayers();
    overlayGroup.clearLayers();
    const geom = bboxPolygon(city.lat, city.lon);
    const layer = L.geoJSON(geom, {
      style: { color: "#10B981", weight: 2, fillColor: "#10B981", fillOpacity: 0.1 },
    }).addTo(drawnItems);
    activeBounds = layer.getBounds();
    map.fitBounds(activeBounds, { padding: [24, 24] });
    areaPill.textContent = `Selected: ${city.label}`;

    const regData = await api.getRegions();
    savedRegions = regData.results || [];
    const existing = savedRegions.find((r) => r.name === city.label);
    if (existing) {
      const anaData = await api.getAnalyses();
      const match = (anaData.results || []).find((a) => a.region === existing.id);
      if (match) {
        await displayAnalysisOnWorkbench(match, existing);
        return;
      }
    }
    rightEl.innerHTML = renderEmptyState(
      `${city.label} selected. Click "Analyze" to retrieve Copernicus Sentinel-2 L2A & NASA POWER data.`
    );
  }

  citySel.addEventListener("change", () => {
    const idx = Number(citySel.value.replace("city:", ""));
    selectCityAndFocus(idx);
  });

  container.querySelector("#exp-analyze-btn").addEventListener("click", async () => {
    statusEl.innerHTML = renderLoadingSkeleton(2);
    try {
      if (drawnGeometry) {
        const idx = Number(citySel.value.replace("city:", ""));
        const city = CITIES[idx];
        const created = await api.createRegion({
          name: `${city.label} — ${cropSel.value}`,
          crop_type: cropSel.value,
          boundary: drawnGeometry,
        });
        drawnGeometry = null;
        await runAnalysisForRegion(created.id);
        return;
      }

      const idx = Number(citySel.value.replace("city:", ""));
      const city = CITIES[idx];
      const regData = await api.getRegions();
      savedRegions = regData.results || [];
      let target = savedRegions.find((r) => r.name === city.label);
      if (!target) {
        target = await api.createRegion({
          name: city.label,
          crop_type: cropSel.value || city.crop,
          boundary: bboxPolygon(city.lat, city.lon),
        });
      }
      await runAnalysisForRegion(target.id);
    } catch (err) {
      statusEl.innerHTML = renderErrorState(err.message, err.traceId, "retry-analyze");
      bindTraceCopyHandlers(statusEl);
    }
  });

  container.querySelector("#exp-near-me-btn").addEventListener("click", () => {
    if (!navigator.geolocation) {
      appendFeedCard("Location", "Browser geolocation is not supported.");
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const lat = pos.coords.latitude;
        const lon = pos.coords.longitude;
        drawnItems.clearLayers();
        overlayGroup.clearLayers();
        drawnGeometry = bboxPolygon(lat, lon, 0.01);
        const layer = L.geoJSON(drawnGeometry, {
          style: { color: "#10B981", weight: 2, fillOpacity: 0.1 },
        }).addTo(drawnItems);
        activeBounds = layer.getBounds();
        map.fitBounds(activeBounds, { padding: [24, 24] });
        areaPill.textContent = "Near Me ROI";
        appendFeedCard("Near Me", `Centered on ${lat.toFixed(4)}, ${lon.toFixed(4)}. Click Analyze.`);
      },
      () => appendFeedCard("Location", "Geolocation permission denied or unavailable.")
    );
  });

  async function handleCopilotQuestion(qText) {
    if (!currentAnalysis || !currentRegion) {
      appendFeedCard("Notice", "Select a city and click Analyze first.");
      return;
    }
    appendFeedCard("You", qText);
    try {
      const ctx = buildCopilotContext(currentAnalysis, currentWeather, currentRegion, currentZones);
      const reply = await api.askCopilot(qText, ctx);
      appendFeedCard(`Agronomic Copilot (${reply.provider})`, reply.answer);
    } catch (err) {
      appendFeedCard("Error", err.message);
    }
  }

  container.querySelectorAll("[data-prompt]").forEach((btn) => {
    btn.addEventListener("click", () => handleCopilotQuestion(btn.getAttribute("data-prompt")));
  });

  container.querySelector("#exp-ask-form").addEventListener("submit", (e) => {
    e.preventDefault();
    const inp = container.querySelector("#exp-ask-input");
    const val = inp.value.trim();
    if (!val) return;
    inp.value = "";
    handleCopilotQuestion(val);
  });

  // Initial load: focus selected city (Delhi NCR) or display latest saved city analysis
  const initialIdx = Number(citySel.value.replace("city:", ""));
  await selectCityAndFocus(initialIdx);
}

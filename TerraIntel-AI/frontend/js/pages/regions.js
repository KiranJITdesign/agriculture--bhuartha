import { api } from "../api.js";
import {
  bindTraceCopyHandlers,
  renderEmptyState,
  renderErrorState,
  renderLoadingSkeleton,
} from "../components/AsyncState.js";
import { initRegionMap } from "../components/RegionMap.js";
import { renderStatCard } from "../components/StatCard.js";

const CITIES = [
  {
    label: "Bengaluru (Karnataka)",
    lat: 13.285,
    lon: 77.745,
    crops: ["Ragi", "Maize", "Paddy", "Tomato", "Chilli"],
  },
  {
    label: "Mumbai (Maharashtra)",
    lat: 19.705,
    lon: 72.865,
    crops: ["Paddy", "Finger Millet", "Pulses", "Vegetables"],
  },
  {
    label: "Chennai (Tamil Nadu)",
    lat: 13.145,
    lon: 79.905,
    crops: ["Paddy", "Groundnut", "Sugarcane", "Chilli", "Pulses"],
  },
  {
    label: "Hyderabad (Telangana)",
    lat: 17.565,
    lon: 78.845,
    crops: ["Paddy", "Cotton", "Chilli", "Maize", "Red Gram"],
  },
  {
    label: "Delhi (Delhi NCR)",
    lat: 28.865,
    lon: 77.085,
    crops: ["Wheat", "Paddy", "Mustard", "Sugarcane", "Vegetables"],
  },
  {
    label: "Pune (Maharashtra)",
    lat: 18.155,
    lon: 74.575,
    crops: ["Sugarcane", "Jowar", "Bajra", "Onion", "Soybean"],
  },
  {
    label: "Kolkata (West Bengal)",
    lat: 22.845,
    lon: 88.455,
    crops: ["Paddy", "Jute", "Potato", "Mustard", "Vegetables"],
  },
];

export async function renderRegionsPage(container) {
  const cityOpts = CITIES.map(
    (c, i) => `<option value="${i}" ${c.label.startsWith("Delhi") ? "selected" : ""}>${c.label}</option>`
  ).join("");

  container.innerHTML = `
    <div class="workbench-3col">
      <div class="pane-scroll">
        <div class="panel">
          <h3>Draw &amp; Save Boundary</h3>
          <form id="region-form" class="region-form">
            <div>
              <label class="field-label" for="reg-city-select">Select City / Region</label>
              <select id="reg-city-select" class="select" required>${cityOpts}</select>
            </div>
            <div>
              <label class="field-label" for="region-crop">Crop type (grown in selected city)</label>
              <select id="region-crop" class="select" required></select>
            </div>
            <div>
              <label class="field-label" for="region-name">Plot label (optional)</label>
              <input id="region-name" class="input" type="text" placeholder="Defaults to selected city & crop">
            </div>
            <div class="stat-card">
              <p class="stat-label">Selected Map Area</p>
              <p id="live-area-ha" class="stat-value">0.00 ha</p>
              <p class="stat-meta">Allowed: 0.10 to 50,000 ha (max 500 vertices)</p>
            </div>
            <div id="region-form-error"></div>
            <button id="save-region-btn" class="btn btn-primary" type="submit" disabled>Save boundary</button>
          </form>
        </div>
        <div class="panel">
          <h3>AI Crop Suitability Note</h3>
          <div id="reg-ai-note" class="copilot-card">Loading crop advisory...</div>
        </div>
      </div>

      <div class="panel map-panel">
        <div id="region-map" class="map-canvas" aria-label="Boundary drawing map"></div>
      </div>

      <div class="pane-scroll">
        <div class="panel">
          <div class="ledger-header">
            <h3>Saved Regions Ledger</h3>
            <span id="regions-count-pill" class="mono stat-meta">0 regions</span>
          </div>
          <div id="regions-kpi" class="grid-2" style="margin-bottom:var(--s-3)"></div>
          <div id="regions-list">${renderLoadingSkeleton(4)}</div>
        </div>
      </div>
    </div>
  `;

  let currentGeometry = null;
  const areaEl = container.querySelector("#live-area-ha");
  const saveBtn = container.querySelector("#save-region-btn");
  const formErrEl = container.querySelector("#region-form-error");
  const citySel = container.querySelector("#reg-city-select");
  const cropSel = container.querySelector("#region-crop");
  const aiNoteEl = container.querySelector("#reg-ai-note");

  const mapController = initRegionMap("region-map", (geom, areaHa) => {
    currentGeometry = geom;
    areaEl.textContent = `${areaHa.toFixed(2)} ha`;
    saveBtn.disabled = !geom;
  });

  async function refreshAiCropNote(cityLabel, cropName) {
    aiNoteEl.textContent = "Querying AI agronomic advisory...";
    try {
      const res = await api.askCopilot(
        `Provide a concise agronomic note for growing ${cropName} in ${cityLabel}.`,
        { region_name: cityLabel, crop_type: cropName }
      );
      aiNoteEl.innerHTML = `<p class="copilot-card-title">${res.provider}</p><div>${res.answer}</div>`;
    } catch {
      aiNoteEl.textContent = `${cropName} is a major seasonal crop in ${cityLabel}. Draw a field boundary on the satellite map to analyze NDVI.`;
    }
  }

  function populateCropsForCity(idx, focusMap = true) {
    const city = CITIES[idx];
    if (!city) return;
    cropSel.innerHTML = city.crops.map((crop) => `<option value="${crop}">${crop}</option>`).join("");
    if (focusMap) mapController.focusLatLon(city.lat, city.lon);
    refreshAiCropNote(city.label, cropSel.value);
  }

  citySel.addEventListener("change", () => populateCropsForCity(Number(citySel.value), true));
  cropSel.addEventListener("change", () => {
    const city = CITIES[Number(citySel.value)];
    if (city) refreshAiCropNote(city.label, cropSel.value);
  });

  populateCropsForCity(Number(citySel.value), true);

  async function loadRegions() {
    const listEl = container.querySelector("#regions-list");
    const kpiEl = container.querySelector("#regions-kpi");
    const countPill = container.querySelector("#regions-count-pill");
    try {
      const data = await api.getRegions();
      const items = data.results || [];
      countPill.textContent = `${items.length} regions`;
      const totalHa = items.reduce((acc, r) => acc + Number(r.area_ha), 0);
      kpiEl.innerHTML = `
        ${renderStatCard({ label: "Total Regions", value: String(items.length) })}
        ${renderStatCard({ label: "Total Area", value: `${totalHa.toFixed(2)} ha` })}
      `;
      if (items.length === 0) {
        listEl.innerHTML = renderEmptyState("No agricultural regions saved yet. Draw a polygon on the satellite map to begin.");
        return;
      }
      listEl.innerHTML = `
        <table class="data-table">
          <thead><tr><th>Name</th><th>Crop</th><th>Area</th><th></th></tr></thead>
          <tbody>
            ${items
              .map(
                (r) => `
              <tr>
                <td><button type="button" class="btn" data-view-region="${r.id}">${r.name}</button></td>
                <td>${r.crop_type || "-"}</td>
                <td class="mono">${r.area_ha} ha</td>
                <td><button type="button" class="btn" data-delete-region="${r.id}">Delete</button></td>
              </tr>`
              )
              .join("")}
          </tbody>
        </table>
      `;
      listEl.querySelectorAll("[data-view-region]").forEach((btn) => {
        btn.addEventListener("click", () => {
          const found = items.find((i) => i.id === btn.getAttribute("data-view-region"));
          if (found) mapController.showRegion(found.boundary);
        });
      });
      listEl.querySelectorAll("[data-delete-region]").forEach((btn) => {
        btn.addEventListener("click", async () => {
          await api.deleteRegion(btn.getAttribute("data-delete-region"));
          loadRegions();
        });
      });
    } catch (err) {
      listEl.innerHTML = renderErrorState(err.message, err.traceId, "retry-regions-btn");
      bindTraceCopyHandlers(listEl);
      listEl.querySelector("#retry-regions-btn")?.addEventListener("click", loadRegions);
    }
  }

  container.querySelector("#region-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!currentGeometry) return;
    formErrEl.innerHTML = "";
    saveBtn.disabled = true;
    const city = CITIES[Number(citySel.value)];
    const selectedCrop = cropSel.value;
    const customLabel = container.querySelector("#region-name").value.trim();
    const regionName = customLabel || `${city.label} — ${selectedCrop}`;
    try {
      await api.createRegion({
        name: regionName,
        crop_type: selectedCrop,
        boundary: currentGeometry,
      });
      container.querySelector("#region-name").value = "";
      areaEl.textContent = "0.00 ha";
      currentGeometry = null;
      await loadRegions();
    } catch (err) {
      formErrEl.innerHTML = renderErrorState(err.message, err.traceId, "retry-save-region");
      bindTraceCopyHandlers(formErrEl);
    } finally {
      saveBtn.disabled = !currentGeometry;
    }
  });

  await loadRegions();
}

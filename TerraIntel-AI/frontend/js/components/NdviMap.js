import { api, apiRequest } from "../api.js";

function resolveMediaUrl(url) {
  if (!url) return "";
  if (url.startsWith("http")) return url;
  return `${window.location.protocol}//${window.location.hostname || "127.0.0.1"}:8010${url}`;
}

export function initNdviMap(containerId, regionGeoJson, tiles, analysisId = null) {
  const map = L.map(containerId).setView([20.5937, 78.9629], 12);
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

  const boundaryLayer = L.geoJSON(regionGeoJson, {
    style: { color: "#10B981", weight: 2, fillColor: "#10B981", fillOpacity: 0.08 },
  }).addTo(map);
  const bounds = boundaryLayer.getBounds();
  map.fitBounds(bounds, { padding: [20, 20] });

  if (analysisId) {
    apiRequest(api.getLowVigourGeoJsonUrl(analysisId))
      .then((geojson) => {
        if (geojson && geojson.features && geojson.features.length > 0) {
          L.geoJSON(geojson, {
            style: { color: "#F59E0B", weight: 2, fillColor: "#EF4444", fillOpacity: 0.35 },
          }).addTo(map);
        }
      })
      .catch(() => {});
  }

  let activeLayer = null;
  function setLayer(mode) {
    if (activeLayer) {
      map.removeLayer(activeLayer);
      activeLayer = null;
    }
    if (!tiles || !tiles.expires_at || Date.now() > Date.parse(tiles.expires_at)) {
      if (mode === "true_colour" && !map.hasLayer(esriSat)) esriSat.addTo(map);
      return false;
    }
    const rawUrl = mode === "true_colour" ? tiles.true_colour_url : tiles.ndvi_url;
    if (!rawUrl) {
      if (mode === "true_colour" && !map.hasLayer(esriSat)) esriSat.addTo(map);
      return true;
    }
    const url = resolveMediaUrl(rawUrl);
    if (url.includes("{z}")) {
      activeLayer = L.tileLayer(url, { opacity: 0.85 }).addTo(map);
    } else {
      activeLayer = L.imageOverlay(url, bounds, { opacity: 0.85 }).addTo(map);
    }
    return true;
  }

  setLayer("ndvi");
  return { map, setLayer };
}

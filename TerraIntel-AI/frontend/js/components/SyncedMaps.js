export function initSyncedMaps(mapIds, regionGeoJson, diffTileUrl) {
  let diffBounds = null;
  const maps = mapIds.map((id) => {
    const m = L.map(id).setView([20.5937, 78.9629], 12);
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
    esriSat.addTo(m);
    labels.addTo(m);
    L.control
      .layers(
        {
          "Satellite (High-Res)": esriSat,
          "Satellite (Sentinel-2)": s2Sat,
          "Street (OSM)": street,
        },
        { "Place & road labels": labels }
      )
      .addTo(m);
    const layer = L.geoJSON(regionGeoJson, {
      style: { color: "#10B981", weight: 2, fillColor: "#10B981", fillOpacity: 0.12 },
    }).addTo(m);
    diffBounds = layer.getBounds();
    m.fitBounds(diffBounds, { padding: [16, 16] });
    return m;
  });

  if (diffTileUrl && maps[2]) {
    const fullUrl = diffTileUrl.startsWith("http")
      ? diffTileUrl
      : `${window.location.protocol}//${window.location.hostname || "127.0.0.1"}:8010${diffTileUrl}`;
    if (fullUrl.includes("{z}")) {
      L.tileLayer(fullUrl, { opacity: 0.85 }).addTo(maps[2]);
    } else if (diffBounds) {
      L.imageOverlay(fullUrl, diffBounds, { opacity: 0.85 }).addTo(maps[2]);
    }
  }

  let syncing = false;
  maps.forEach((source) => {
    source.on("move", () => {
      if (syncing) return;
      syncing = true;
      const center = source.getCenter();
      const zoom = source.getZoom();
      maps.forEach((target) => {
        if (target !== source) target.setView(center, zoom, { animate: false });
      });
      syncing = false;
    });
  });

  return maps;
}

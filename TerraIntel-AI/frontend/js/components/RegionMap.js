function ringAreaHa(latLngs) {
  if (!window.L || !L.GeometryUtil || !latLngs || latLngs.length < 3) {
    // Spherical excess fallback (ha)
    const R = 6378137;
    let area = 0;
    const len = latLngs.length;
    for (let i = 0; i < len; i += 1) {
      const p1 = latLngs[i];
      const p2 = latLngs[(i + 1) % len];
      area +=
        ((p2.lng - p1.lng) * Math.PI) / 180 *
        (2 + Math.sin((p1.lat * Math.PI) / 180) + Math.sin((p2.lat * Math.PI) / 180));
    }
    return Math.abs((area * R * R) / 2) / 10000;
  }
  return L.GeometryUtil.geodesicArea(latLngs) / 10000;
}

export function initRegionMap(containerId, onPolygonChange) {
  const map = L.map(containerId).setView([20.5937, 78.9629], 5);
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
  map.addLayer(drawnItems);

  const drawControl = new L.Control.Draw({
    edit: { featureGroup: drawnItems },
    draw: {
      polygon: { allowIntersection: false, showArea: true },
      polyline: false,
      rectangle: true,
      circle: false,
      circlemarker: false,
      marker: false,
    },
  });
  map.addControl(drawControl);

  function emitGeometry() {
    const layers = drawnItems.getLayers();
    if (layers.length === 0) {
      onPolygonChange(null, 0);
      return;
    }
    const layer = layers[0];
    const geojson = layer.toGeoJSON().geometry;
    const latLngs = layer.getLatLngs()[0] || [];
    onPolygonChange(geojson, ringAreaHa(latLngs));
  }

  map.on(L.Draw.Event.CREATED, (e) => {
    drawnItems.clearLayers();
    drawnItems.addLayer(e.layer);
    emitGeometry();
  });
  map.on(L.Draw.Event.EDITED, emitGeometry);
  map.on(L.Draw.Event.DELETED, emitGeometry);

  return {
    map,
    focusLatLon: (lat, lon) => map.setView([lat, lon], 14),
    showRegion: (geojson) => {
      drawnItems.clearLayers();
      const layer = L.geoJSON(geojson);
      layer.eachLayer((l) => drawnItems.addLayer(l));
      map.fitBounds(drawnItems.getBounds(), { padding: [20, 20] });
    },
  };
}

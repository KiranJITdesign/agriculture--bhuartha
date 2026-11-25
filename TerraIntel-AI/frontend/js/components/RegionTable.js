export function renderRegionTable(container, regions, latestByRegion) {
  if (regions.length === 0) {
    container.innerHTML = "<p>No regions registered.</p>";
    return;
  }
  const rows = regions
    .map((r) => {
      const a = latestByRegion.get(r.id);
      const ndvi = a ? `${a.mean_ndvi} (cov ${a.valid_pixel_pct}%)` : "Not analysed";
      return `
        <tr>
          <td>${r.name}</td>
          <td>${r.crop_type || "-"}</td>
          <td class="mono">${r.area_ha} ha</td>
          <td class="mono">${ndvi}</td>
        </tr>
      `;
    })
    .join("");

  container.innerHTML = `
    <table class="data-table">
      <thead><tr><th>Region</th><th>Crop</th><th>Area</th><th>Latest NDVI</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>
  `;
}

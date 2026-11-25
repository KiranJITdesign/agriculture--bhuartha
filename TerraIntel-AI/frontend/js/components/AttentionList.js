export function renderAttentionList(container, analyses, regionNameById) {
  const flagged = analyses.filter((a) => Number(a.relative_low_area_ha) > 0 || Number(a.absolute_low_area_ha) > 0);
  if (flagged.length === 0) {
    container.innerHTML = "<p>No regions currently flagged for low vegetation greenness.</p>";
    return;
  }
  const items = flagged
    .map(
      (a) => `
      <li>
        <strong>${regionNameById.get(a.region) || a.region}</strong>:
        <span class="mono">${a.relative_low_area_ha} ha</span> relative low greenness
        (<span class="mono">${a.valid_pixel_pct}%</span> coverage)
      </li>`
    )
    .join("");
  container.innerHTML = `<ul>${items}</ul>`;
}

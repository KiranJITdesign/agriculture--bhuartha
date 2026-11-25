export function renderStatCard({ label, value, meta = "" }) {
  const metaHtml = meta ? `<p class="stat-meta">${meta}</p>` : "";
  return `
    <div class="stat-card">
      <p class="stat-label">${label}</p>
      <p class="stat-value">${value}</p>
      ${metaHtml}
    </div>
  `;
}

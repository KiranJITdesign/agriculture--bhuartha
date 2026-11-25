/**
 * Reusable async UI state renderers (loading, empty, error with trace_id copy, partial coverage).
 */
export function renderLoadingSkeleton(lines = 4) {
  const rows = Array.from({ length: lines }, () => '<div class="skeleton-block"></div>').join("");
  return `<div class="panel" aria-busy="true" aria-label="Loading">${rows}</div>`;
}

export function renderEmptyState(message, actionLabel = "", actionHref = "") {
  const action = actionLabel && actionHref
    ? `<p><a class="btn btn-primary" href="${actionHref}">${actionLabel}</a></p>`
    : "";
  return `<div class="panel prose"><p>${message}</p>${action}</div>`;
}

export function renderErrorState(message, traceId = "", retryId = "retry-btn") {
  const traceBlock = traceId
    ? `<p class="mono">trace_id: ${traceId} <button type="button" class="btn" data-copy-trace="${traceId}">Copy trace_id</button></p>`
    : "";
  return `
    <div class="banner banner-error" role="alert">
      <p>${message}</p>
      ${traceBlock}
      <button type="button" class="btn" id="${retryId}">Retry</button>
    </div>
  `;
}

export function renderCoverageBanner(validPixelPct) {
  return `
    <div class="banner banner-warning" role="status">
      Insufficient cloud-free coverage (${validPixelPct}% valid cropland pixels, threshold 30%). Interpret vegetation statistics with caution.
    </div>
  `;
}

export function bindTraceCopyHandlers(container) {
  container.querySelectorAll("[data-copy-trace]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const tid = btn.getAttribute("data-copy-trace") || "";
      if (navigator.clipboard && tid) {
        navigator.clipboard.writeText(tid);
        btn.textContent = "Copied";
      }
    });
  });
}

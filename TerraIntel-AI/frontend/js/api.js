/**
 * Central API client — the ONLY module permitted to call fetch().
 * Handles base URL, JSON/problem+json parsing, and trace_id extraction.
 */
const API_BASE =
  window.TERRAINTEL_API_BASE ||
  `${window.location.protocol}//${window.location.hostname || "127.0.0.1"}:8010`;

export class ApiError extends Error {
  constructor(message, { status = 500, code = "API_ERROR", traceId = "", detail = null } = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.traceId = traceId;
    this.detail = detail;
  }
}

export async function apiRequest(path, options = {}) {
  const url = path.startsWith("http") ? path : `${API_BASE}${path}`;
  const headers = {
    Accept: "application/json",
    ...(options.body ? { "Content-Type": "application/json" } : {}),
    ...(options.headers || {}),
  };

  let response;
  try {
    response = await fetch(url, { ...options, headers });
  } catch (err) {
    throw new ApiError("Network request failed.", {
      status: 0,
      code: "NETWORK_ERROR",
      detail: err.message,
    });
  }

  const contentType = response.headers.get("content-type") || "";
  const isJson = contentType.includes("json");
  const data = isJson ? await response.json() : await response.text();

  if (!response.ok) {
    const traceId = (isJson && data?.trace_id) || response.headers.get("x-trace-id") || "";
    const code = (isJson && data?.code) || "API_ERROR";
    const detail = isJson ? data?.detail || data?.title || "Request failed" : String(data);
    throw new ApiError(typeof detail === "string" ? detail : JSON.stringify(detail), {
      status: response.status,
      code,
      traceId,
      detail,
    });
  }

  return data;
}

export async function apiDownloadBlob(path, options = {}, filename = "report.pdf") {
  const url = path.startsWith("http") ? path : `${API_BASE}${path}`;
  const response = await fetch(url, {
    ...options,
    headers: {
      ...(options.body ? { "Content-Type": "application/json" } : {}),
      ...(options.headers || {}),
    },
  });
  if (!response.ok) {
    throw new ApiError("Download failed.", { status: response.status });
  }
  const blob = await response.blob();
  const objUrl = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = objUrl;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(objUrl);
}

export const api = {
  getRegions: () => apiRequest("/api/v1/regions/"),
  createRegion: (payload) => apiRequest("/api/v1/regions/", { method: "POST", body: JSON.stringify(payload) }),
  deleteRegion: (id) => apiRequest(`/api/v1/regions/${id}/`, { method: "DELETE" }),
  submitJob: (payload) => apiRequest("/api/v1/jobs/", { method: "POST", body: JSON.stringify(payload) }),
  getJob: (id) => apiRequest(`/api/v1/jobs/${id}/`),
  getAnalyses: () => apiRequest("/api/v1/analyses/"),
  getAnalysis: (id) => apiRequest(`/api/v1/analyses/${id}/`),
  getWeather: (regionId, startDate, endDate) =>
    apiRequest(`/api/v1/weather/?region=${encodeURIComponent(regionId)}&start_date=${startDate}&end_date=${endDate}`),
  comparePeriods: (payload) => apiRequest("/api/v1/compare/", { method: "POST", body: JSON.stringify(payload) }),
  askCopilot: (question, context) =>
    apiRequest("/api/v1/copilot/", { method: "POST", body: JSON.stringify({ question, context }) }),
  getLowVigourGeoJsonUrl: (analysisId) => `${API_BASE}/api/v1/analyses/${analysisId}/low-vigour.geojson`,
  getReportPdfUrl: (analysisId) => `${API_BASE}/api/v1/analyses/${analysisId}/report.pdf`,
  downloadCompareReportPdf: (payload) =>
    apiDownloadBlob(
      "/api/v1/compare/report.pdf",
      { method: "POST", body: JSON.stringify(payload) },
      `compare-report-${payload.region}.pdf`
    ),
  searchNominatim: async (query) => {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 10000);
    try {
      const url = `https://nominatim.openstreetmap.org/search?format=json&limit=5&q=${encodeURIComponent(query)}`;
      return await apiRequest(url, { signal: controller.signal });
    } finally {
      clearTimeout(timer);
    }
  },
};

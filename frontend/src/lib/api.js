const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

export async function createRun(files, userContext = "") {
  const formData = new FormData();
  files.forEach((file) => formData.append("images", file));
  if (userContext) {
    formData.append("user_context", userContext);
  }

  const res = await fetch(`${API_BASE}/api/v1/runs`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    throw new Error(`Failed to create run (${res.status})`);
  }
  return res.json();
}

export async function getRun(runId) {
  const res = await fetch(`${API_BASE}/api/v1/runs/${runId}`);
  if (!res.ok) {
    throw new Error(`Failed to get run (${res.status})`);
  }
  return res.json();
}

export async function getReport(runId) {
  const res = await fetch(`${API_BASE}/api/v1/runs/${runId}/report`);
  if (!res.ok) {
    throw new Error(`Failed to get report (${res.status})`);
  }
  return res.json();
}

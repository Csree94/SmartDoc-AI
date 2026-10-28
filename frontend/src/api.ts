import type { ChatResponse, UploadResult } from "./types";

const API_BASE_URL =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ??
  "http://127.0.0.1:8000";

async function readError(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === "string") return body.detail;
  } catch {
    // response had no JSON body
  }
  return `Request failed with HTTP status ${response.status}`;
}

export async function uploadDocument(file: File): Promise<UploadResult> {
  if (!file.name.toLowerCase().endsWith(".pdf") && !file.name.toLowerCase().endsWith(".txt")) {
    return Promise.reject(new Error("Only PDF and TXT files are supported."));
  }
  const form = new FormData();
  form.append("file", file);
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/upload`, { method: "POST", body: form });
  } catch {
    throw new Error("Cannot reach the backend. Is it running on " + API_BASE_URL + "?");
  }
  if (!response.ok) {
    throw new Error(await readError(response));
  }
  const result = (await response.json()) as UploadResult;
  if (result.status !== "indexed") {
    throw new Error("The backend did not confirm indexing succeeded.");
  }
  return result;
}

export async function askQuestion(question: string): Promise<ChatResponse> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
  } catch {
    throw new Error("Cannot reach the backend. Is it running on " + API_BASE_URL + "?");
  }
  if (!response.ok) {
    throw new Error(await readError(response));
  }
  let body: unknown;
  try {
    body = await response.json();
  } catch {
    throw new Error("The backend returned a malformed response.");
  }
  if (
    typeof (body as ChatResponse).answer !== "string" ||
    !Array.isArray((body as ChatResponse).doc_sources) ||
    !Array.isArray((body as ChatResponse).web_sources)
  ) {
    throw new Error("The backend returned an unexpected response format.");
  }
  return body as ChatResponse;
}

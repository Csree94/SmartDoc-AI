export interface DocSource {
  filename: string;
  page: number;
  similarity: number;
}

export interface WebSource {
  title: string;
  url: string;
}

export interface ChatResponse {
  answer: string;
  used_web_search: boolean;
  doc_sources: DocSource[];
  web_sources: WebSource[];
}

export interface UploadResult {
  status: string;
  filename: string;
  pages: number;
  chunks: number;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  docSources?: DocSource[];
  webSources?: WebSource[];
  usedWebSearch?: boolean;
  error?: string;
}

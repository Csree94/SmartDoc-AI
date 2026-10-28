import { useCallback, useRef, useState } from "react";
import { askQuestion, uploadDocument } from "./api";
import type { ChatMessage } from "./types";

const initialMessages: ChatMessage[] = [];

function SourceBadges({ docSources, webSources, usedWebSearch }: {
  docSources: ChatMessage["docSources"];
  webSources: ChatMessage["webSources"];
  usedWebSearch: boolean;
}) {
  if (!docSources?.length && !webSources?.length && !usedWebSearch) return null;
  return (
    <div className="sources">
      {usedWebSearch && <span className="badge web-flag">🌐 Web search used</span>}
      {docSources?.map((s, i) => (
        <span key={`d${i}`} className="badge doc">
          📄 {s.filename}, page {s.page} ({(s.similarity * 100).toFixed(0)}% match)
        </span>
      ))}
      {webSources?.map((s, i) =>
        s.title || s.url ? (
          <a key={`w${i}`} className="badge web" href={s.url} target="_blank" rel="noreferrer">
            🔗 {s.title || s.url}
          </a>
        ) : null
      )}
    </div>
  );
}

export default function App() {
  const [messages, setMessages] = useState<ChatMessage[]>(initialMessages);
  const [question, setQuestion] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const [uploadLoading, setUploadLoading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const sendQuestion = useCallback(async () => {
    const q = question.trim();
    if (!q || chatLoading) return;
    setMessages((m) => [...m, { role: "user", content: q }]);
    setQuestion("");
    setChatLoading(true);
    try {
      const res = await askQuestion(q);
      setMessages((m) => [
        ...m,
        {
          role: "assistant",
          content: res.answer,
          docSources: res.doc_sources,
          webSources: res.web_sources,
          usedWebSearch: res.used_web_search,
        },
      ]);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unknown error";
      setMessages((m) => [...m, { role: "assistant", content: "", error: message }]);
    } finally {
      setChatLoading(false);
    }
  }, [question, chatLoading]);

  const onUpload = useCallback(async (file: File) => {
    setUploadLoading(true);
    setUploadStatus(null);
    setUploadError(null);
    try {
      const res = await uploadDocument(file);
      setUploadStatus(
        `✅ Indexed "${res.filename}": ${res.pages} page(s), ${res.chunks} chunk(s).`
      );
    } catch (err) {
      setUploadStatus(null);
      setUploadError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploadLoading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }, []);

  const onFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) void onUpload(file);
    },
    [onUpload]
  );

  const onKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        void sendQuestion();
      }
    },
    [sendQuestion]
  );

  return (
    <div className="app">
      <header className="header">
        <h1>SmartDoc AI</h1>
        <p>Chat with your documents and search the web.</p>
      </header>

      <section className="upload-panel">
        <label htmlFor="file-input" className="upload-label">
          Upload a document (PDF or TXT):
        </label>
        <input
          id="file-input"
          ref={fileInputRef}
          type="file"
          accept=".pdf,.txt,application/pdf,text/plain"
          onChange={onFileChange}
          disabled={uploadLoading}
        />
        {uploadLoading && <span className="status loading">⏳ Indexing document…</span>}
        {uploadStatus && <span className="status success">{uploadStatus}</span>}
        {uploadError && <span className="status error">⚠ {uploadError}</span>}
      </section>

      <main className="chat" aria-live="polite">
        {messages.length === 0 && !chatLoading && (
          <p className="empty-hint">
            Upload a document, then ask a question about it. The assistant answers from
            your documents first, and searches the web when the documents are not enough.
          </p>
        )}
        {messages.map((m, i) =>
          m.role === "user" ? (
            <div key={i} className="message user">
              <div className="bubble">{m.content}</div>
            </div>
          ) : (
            <div key={i} className="message assistant">
              <div className="bubble">
                {m.error ? <span className="error-text">⚠ {m.error}</span> : m.content}
                {!m.error && (
                  <SourceBadges
                    docSources={m.docSources}
                    webSources={m.webSources}
                    usedWebSearch={Boolean(m.usedWebSearch)}
                  />
                )}
              </div>
            </div>
          )
        )}
        {chatLoading && (
          <div className="message assistant">
            <div className="bubble loading-bubble">Thinking…</div>
          </div>
        )}
      </main>

      <footer className="composer">
        <textarea
          aria-label="Your question"
          placeholder="Ask about your documents (Enter to send, Shift+Enter for a new line)…"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={onKeyDown}
          rows={2}
          disabled={chatLoading}
        />
        <button onClick={() => void sendQuestion()} disabled={chatLoading || !question.trim()}>
          {chatLoading ? "Sending…" : "Send"}
        </button>
      </footer>
    </div>
  );
}

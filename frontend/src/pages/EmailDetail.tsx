import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { api } from "../lib/api";
import { EmailOut, EmailAnalysis, ReplyOut, EmailAccountOut } from "../types";

const priorityDotColor: Record<string, string> = {
  high: "bg-danger",
  medium: "bg-warn",
  low: "bg-accent2",
};

export default function EmailDetail() {
  const { id } = useParams<{ id: string }>();
  const { token } = useAuth();
  const [email, setEmail] = useState<EmailOut | null>(null);
  const [analysis, setAnalysis] = useState<EmailAnalysis | null>(null);
  const [replies, setReplies] = useState<ReplyOut[]>([]);
  const [loadingReplies, setLoadingReplies] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sentIds, setSentIds] = useState<Set<string>>(new Set());
  const [regeneratingId, setRegeneratingId] = useState<string | null>(null);
  const [accounts, setAccounts] = useState<EmailAccountOut[]>([]);
  const [selectedAccountId, setSelectedAccountId] = useState<string>("");

  async function loadEmail() {
    if (!token || !id) return;
    setError(null);
    try {
      const e = await api.getEmail(token, id);
      setEmail(e);
      await generateReplies();
    } catch (e: any) {
      setError(e.message);
    }
  }

  async function generateReplies() {
    if (!token || !id) return;
    setLoadingReplies(true);
    setError(null);
    try {
      const result = await api.generateReplies(token, id);
      setAnalysis(result.analysis);
      setReplies(result.replies);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoadingReplies(false);
    }
  }

  useEffect(() => {
    loadEmail();
    if (token) {
      api.listAccounts(token).then((accs) => {
        setAccounts(accs);
        if (accs.length > 0) setSelectedAccountId(accs[0].id);
      }).catch(() => {});
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, token]);

  async function handleRegenerate(replyId: string) {
    if (!token) return;
    setRegeneratingId(replyId);
    try {
      const updated = await api.regenerateReply(token, replyId);
      setReplies((prev) => prev.map((r) => (r.id === replyId ? updated : r)));
    } catch (e: any) {
      setError(e.message);
    } finally {
      setRegeneratingId(null);
    }
  }

  async function handleSend(replyId: string) {
    if (!token || !id) return;
    try {
      await api.sendReply(token, id, replyId, selectedAccountId || undefined);
      setSentIds((prev) => new Set(prev).add(replyId));
    } catch (e: any) {
      setError(e.message);
    }
  }

  function handleCopy(body: string) {
    navigator.clipboard.writeText(body);
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <div className="text-[22px] font-semibold font-display">Email detail</div>
          <div className="text-textDim text-[13px] mt-0.5">Review the AI's understanding and pick a reply.</div>
        </div>
        <Link to="/inbox" className="btn btn-ghost">
          ← Back to inbox
        </Link>
      </div>

      {error && <div className="bg-danger/10 text-danger text-[13px] px-3 py-2.5 rounded-lg mb-4">{error}</div>}

      <div className="grid grid-cols-[1fr_1.35fr] gap-4.5 items-start">
        <div className="card">
          {!email ? (
            <div className="text-textFaint text-[13px]">Loading…</div>
          ) : (
            <>
              <div className="text-[15px] font-semibold mb-0.5">{email.sender}</div>
              <div className="text-[12px] text-textFaint mb-4">{new Date(email.received_at).toLocaleString()}</div>
              <div className="font-display text-[16px] font-semibold mb-3.5">{email.subject}</div>
              <div className="text-textDim text-[13.5px] leading-relaxed whitespace-pre-line">{email.body}</div>
            </>
          )}
        </div>

        <div>
          <div className="card mb-4">
            {loadingReplies && !analysis ? (
              <div className="text-textFaint text-[13px] flex items-center gap-2">
                <span className="spinner" /> Calling Claude — analyzing intent, tone, and drafting 10 replies…
              </div>
            ) : analysis ? (
              <>
                <div className="text-[14.5px] font-semibold mb-3">AI analysis</div>
                <div className="grid grid-cols-2 gap-x-5 gap-y-3 mb-3.5">
                  <div>
                    <div className="text-[11px] text-textFaint uppercase tracking-wide mb-1">Intent</div>
                    <div className="text-[13px] font-semibold">{analysis.intent}</div>
                  </div>
                  <div>
                    <div className="text-[11px] text-textFaint uppercase tracking-wide mb-1">Priority</div>
                    <div className="text-[13px] font-semibold">
                      <span
                        className={`inline-block w-1.5 h-1.5 rounded-full mr-1.5 ${priorityDotColor[analysis.priority]}`}
                      />
                      {analysis.priority}
                    </div>
                  </div>
                  <div>
                    <div className="text-[11px] text-textFaint uppercase tracking-wide mb-1">Tone</div>
                    <div className="text-[13px] font-semibold">{analysis.tone}</div>
                  </div>
                  <div>
                    <div className="text-[11px] text-textFaint uppercase tracking-wide mb-1">Required action</div>
                    <div className="text-[13px] font-semibold">{analysis.required_action}</div>
                  </div>
                </div>
                <div className="bg-surface2 border border-borderSoft rounded-lg px-3.5 py-3 text-[12.5px] text-textDim leading-relaxed">
                  <strong className="text-text">Summary — </strong>
                  {analysis.summary}
                </div>
              </>
            ) : (
              <div className="text-textFaint text-[13px]">Waiting on analysis…</div>
            )}
          </div>

          <div className="flex justify-between items-center mb-3">
            <div className="text-[14.5px] font-semibold">Suggested replies</div>
            <button className="btn btn-ghost btn-sm" onClick={generateReplies} disabled={loadingReplies}>
              {loadingReplies ? <span className="spinner" /> : "↻ Regenerate all"}
            </button>
          </div>

          {accounts.length > 0 && (
            <div className="mb-3.5">
              <label className="block text-[11px] text-textFaint uppercase tracking-wide mb-1.5">Reply from</label>
              <select
                className="w-full bg-surface2 border border-border rounded-lg px-3 py-2 text-[13px] text-text outline-none focus:border-accent"
                value={selectedAccountId}
                onChange={(e) => setSelectedAccountId(e.target.value)}
              >
                {accounts.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.email_address} ({a.provider})
                  </option>
                ))}
              </select>
            </div>
          )}

          {replies.map((r, i) => (
            <div
              key={r.id}
              className={`card mb-2.5 !p-4 ${sentIds.has(r.id) ? "border-accent2 bg-accent2/5" : ""}`}
            >
              <div className="flex justify-between items-center mb-2">
                <div className="text-[12px] font-semibold text-[#c7c9ff] flex items-center gap-1.5">
                  <span className="w-[19px] h-[19px] rounded-[6px] bg-surface3 flex items-center justify-center text-[10.5px] font-mono text-textDim">
                    {i + 1}
                  </span>
                  {r.style}
                </div>
                <div className="flex gap-1.5">
                  <button
                    className="w-7 h-7 rounded-md bg-surface2 border border-border text-textDim hover:bg-surface3 hover:text-text flex items-center justify-center"
                    title="Regenerate"
                    onClick={() => handleRegenerate(r.id)}
                    disabled={regeneratingId === r.id}
                  >
                    {regeneratingId === r.id ? <span className="spinner" /> : "↻"}
                  </button>
                  <button
                    className="w-7 h-7 rounded-md bg-surface2 border border-border text-textDim hover:bg-surface3 hover:text-text flex items-center justify-center"
                    title="Copy"
                    onClick={() => handleCopy(r.body)}
                  >
                    ⧉
                  </button>
                </div>
              </div>
              <div className="text-[13px] text-textDim leading-relaxed mb-2.5 whitespace-pre-wrap">{r.body}</div>
              <button className="btn btn-primary btn-sm" onClick={() => handleSend(r.id)}>
                {sentIds.has(r.id) ? "Sent ✓" : "Send this reply"}
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

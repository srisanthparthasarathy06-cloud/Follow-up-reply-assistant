import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { api } from "../lib/api";
import { EmailOut } from "../types";

function StatusTag({ status }: { status: string }) {
  if (status === "completed") return <span className="tag bg-accent2/15 text-accent2">Completed</span>;
  if (status === "failed") return <span className="tag bg-danger/15 text-danger">Failed</span>;
  return <span className="tag bg-surface3 text-textDim">{status.replace("_", " ")}</span>;
}

export default function Dashboard() {
  const { token } = useAuth();
  const [emails, setEmails] = useState<EmailOut[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    if (!token) return;
    try {
      setEmails(await api.listEmails(token));
    } catch (e: any) {
      setError(e.message);
    }
  }

  useEffect(() => {
    load();
  }, [token]);

  const total = emails?.length ?? 0;
  const completed = emails?.filter((e) => e.status === "completed").length ?? 0;
  const pending = emails?.filter((e) => e.status !== "completed").length ?? 0;
  const totalReplies = emails?.reduce((s, e) => s + (e.reply_count || 0), 0) ?? 0;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <div className="text-[22px] font-semibold font-display">Good day 👋</div>
          <div className="text-textDim text-[13px] mt-0.5">
            {emails ? `${total} emails synced · ${completed} processed · ${pending} pending` : "Loading your inbox…"}
          </div>
        </div>
        <div className="flex gap-2.5">
          <button className="btn btn-ghost" onClick={load}>
            ↻ Refresh
          </button>
          <Link to="/bulk" className="btn btn-primary">
            Start Processing
          </Link>
        </div>
      </div>

      {error && <div className="bg-danger/10 text-danger text-[13px] px-3 py-2.5 rounded-lg mb-4">{error}</div>}

      <div className="grid grid-cols-4 gap-3.5 mb-4.5">
        <div className="card">
          <div className="font-display text-[26px] font-semibold">{total || "–"}</div>
          <div className="text-textDim text-[12.5px] mt-1">Total emails</div>
        </div>
        <div className="card">
          <div className="font-display text-[26px] font-semibold">{completed || "–"}</div>
          <div className="text-textDim text-[12.5px] mt-1">Processed</div>
        </div>
        <div className="card">
          <div className="font-display text-[26px] font-semibold">{totalReplies || "–"}</div>
          <div className="text-textDim text-[12.5px] mt-1">Replies generated</div>
        </div>
        <div className="card">
          <div className="font-display text-[26px] font-semibold">{pending || "–"}</div>
          <div className="text-textDim text-[12.5px] mt-1">Pending</div>
        </div>
      </div>

      <div className="relative overflow-hidden rounded-2xl border border-border p-7 mb-4.5 bg-gradient-to-br from-[#171a2c] via-[#12141d] to-surface flex items-center justify-between gap-5">
        <div className="max-w-[560px]">
          <div className="inline-flex items-center gap-1.5 bg-accent/15 text-[#b7b9ff] text-[11.5px] font-semibold px-2.5 py-1 rounded-full mb-3">
            ⚡ Bulk AI processing
          </div>
          <div className="text-[21px] font-semibold mb-2 font-display">Process your inbox with AI</div>
          <div className="text-textDim text-[13.5px] leading-relaxed">
            Relay reads intent, tone and urgency for every message, then drafts 10 distinct reply options per email
            using Claude.
          </div>
        </div>
        <div className="text-right shrink-0">
          <div className="font-display text-[30px] font-bold">10</div>
          <div className="text-[11.5px] text-textFaint mb-3.5">replies / email</div>
          <Link to="/bulk" className="btn btn-primary">
            Start Processing →
          </Link>
        </div>
      </div>

      <div className="card">
        <div className="flex justify-between items-center mb-3.5">
          <div className="text-[14.5px] font-semibold">Recent emails</div>
          <Link to="/inbox" className="text-[12px] text-textDim">
            View inbox →
          </Link>
        </div>
        {!emails ? (
          <div className="text-textFaint text-[13px] text-center py-5">Loading…</div>
        ) : emails.length === 0 ? (
          <div className="text-textFaint text-[13px] text-center py-5">
            No emails yet — run <span className="font-mono">python seed.py</span> in your backend folder, then
            Refresh.
          </div>
        ) : (
          emails.slice(0, 6).map((e) => (
            <Link
              to={`/inbox/${e.id}`}
              key={e.id}
              className="flex items-center gap-3 py-2.5 border-b border-borderSoft last:border-0 hover:bg-surface2 rounded-lg px-1.5 -mx-1.5"
            >
              <div className="w-8 h-8 rounded-full bg-surface3 flex items-center justify-center text-[11.5px] font-semibold text-textDim shrink-0">
                {e.sender.slice(0, 2).toUpperCase()}
              </div>
              <div className="flex-1 min-w-0">
                <div className="font-semibold text-[13px] truncate">{e.sender}</div>
                <div className="text-textDim text-[12.5px] truncate">{e.subject}</div>
              </div>
              <span className="tag bg-accent/15 text-[#b7b9ff]">{e.intent || "Not analyzed"}</span>
              <StatusTag status={e.status} />
            </Link>
          ))
        )}
      </div>
    </div>
  );
}

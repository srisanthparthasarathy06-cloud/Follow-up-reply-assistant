import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { api } from "../lib/api";
import { EmailOut } from "../types";

const priorityDotColor: Record<string, string> = {
  high: "bg-danger",
  medium: "bg-warn",
  low: "bg-accent2",
};

export default function Inbox() {
  const { token } = useAuth();
  const [emails, setEmails] = useState<EmailOut[] | null>(null);
  const [search, setSearch] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function load() {
    if (!token) return;
    try {
      setEmails(await api.listEmails(token, search || undefined));
    } catch (e: any) {
      setError(e.message);
    }
  }

  useEffect(() => {
    const t = setTimeout(load, 250);
    return () => clearTimeout(t);
  }, [token, search]);

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <div className="text-[22px] font-semibold font-display">Inbox</div>
          <div className="text-textDim text-[13px] mt-0.5">{emails ? `${emails.length} emails` : "—"}</div>
        </div>
        <Link to="/bulk" className="btn btn-primary">
          Process pending
        </Link>
      </div>

      {error && <div className="bg-danger/10 text-danger text-[13px] px-3 py-2.5 rounded-lg mb-4">{error}</div>}

      <div className="mb-4">
        <input
          className="bg-surface border border-border rounded-lg px-3 py-2 text-[13px] w-[280px] outline-none focus:border-accent"
          placeholder="Search by sender or subject…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      <div className="card !p-0">
        <table className="w-full border-collapse">
          <thead>
            <tr>
              {["Sender", "Subject", "Intent", "Priority", "Status", "Replies"].map((h) => (
                <th
                  key={h}
                  className="text-left text-[11px] uppercase tracking-wide text-textFaint font-semibold px-3.5 pb-2.5 pt-3.5 border-b border-borderSoft"
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {!emails ? (
              <tr>
                <td colSpan={6} className="text-textFaint text-[13px] text-center py-6">
                  Loading…
                </td>
              </tr>
            ) : emails.length === 0 ? (
              <tr>
                <td colSpan={6} className="text-textFaint text-[13px] text-center py-6">
                  No emails found.
                </td>
              </tr>
            ) : (
              emails.map((e) => (
                <tr key={e.id} className="hover:bg-surface2 cursor-pointer">
                  <td className="px-3.5 py-3 border-b border-borderSoft font-semibold text-[13px]">
                    <Link to={`/inbox/${e.id}`} className="block">
                      {e.sender}
                    </Link>
                  </td>
                  <td className="px-3.5 py-3 border-b border-borderSoft text-textDim text-[13px]">
                    <Link to={`/inbox/${e.id}`} className="block">
                      {e.subject}
                    </Link>
                  </td>
                  <td className="px-3.5 py-3 border-b border-borderSoft">
                    <span className="tag bg-accent/15 text-[#b7b9ff]">{e.intent || "—"}</span>
                  </td>
                  <td className="px-3.5 py-3 border-b border-borderSoft text-[13px]">
                    {e.priority ? (
                      <>
                        <span className={`inline-block w-1.5 h-1.5 rounded-full mr-1.5 ${priorityDotColor[e.priority]}`} />
                        {e.priority[0].toUpperCase() + e.priority.slice(1)}
                      </>
                    ) : (
                      "—"
                    )}
                  </td>
                  <td className="px-3.5 py-3 border-b border-borderSoft">
                    {e.status === "completed" ? (
                      <span className="tag bg-accent2/15 text-accent2">Completed</span>
                    ) : e.status === "failed" ? (
                      <span className="tag bg-danger/15 text-danger">Failed</span>
                    ) : (
                      <span className="tag bg-surface3 text-textDim">{e.status.replace("_", " ")}</span>
                    )}
                  </td>
                  <td className="px-3.5 py-3 border-b border-borderSoft font-mono text-textFaint text-[13px]">
                    {e.reply_count || "—"}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

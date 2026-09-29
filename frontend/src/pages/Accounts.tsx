import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { api } from "../lib/api";
import { EmailAccountOut } from "../types";

export default function Accounts() {
  const { token } = useAuth();
  const [params] = useSearchParams();
  const [accounts, setAccounts] = useState<EmailAccountOut[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(
    params.get("connected") ? "Gmail connected. Click “Sync inbox” to pull your emails." : null
  );
  const [busyId, setBusyId] = useState<string | null>(null);
  const [connecting, setConnecting] = useState(false);

  async function load() {
    if (!token) return;
    try {
      setAccounts(await api.listAccounts(token));
    } catch (e: any) {
      setError(e.message);
    }
  }

  useEffect(() => {
    load();
  }, [token]);

  async function connectGmail() {
    if (!token) return;
    setConnecting(true);
    setError(null);
    try {
      const { url } = await api.googleConnectUrl(token);
      window.location.href = api.base + url; // leaves the SPA for Google's consent screen
    } catch (e: any) {
      setError(e.message);
      setConnecting(false);
    }
  }

  async function sync(id: string) {
    if (!token) return;
    setBusyId(id);
    setError(null);
    setNotice(null);
    try {
      const r = await api.syncAccount(token, id, 50);
      setNotice(`Fetched ${r.fetched} emails — ${r.added} new, ${r.skipped_duplicates} already synced.`);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusyId(null);
    }
  }

  async function disconnect(id: string) {
    if (!token || !confirm("Disconnect this account? Already-synced emails stay in Relay.")) return;
    try {
      await api.disconnectAccount(token, id);
      await load();
    } catch (e: any) {
      setError(e.message);
    }
  }

  return (
    <div>
      <div className="mb-6">
        <div className="text-[22px] font-semibold font-display">Email accounts</div>
        <div className="text-textDim text-[13px] mt-0.5">
          Connect with Google OAuth — Relay never sees or stores your password.
        </div>
      </div>

      {error && <div className="bg-danger/10 text-danger text-[13px] px-3 py-2.5 rounded-lg mb-4">{error}</div>}
      {notice && (
        <div className="bg-accent2/10 text-accent2 text-[13px] px-3 py-2.5 rounded-lg mb-4">
          {notice}{" "}
          <Link to="/inbox" className="underline">
            Open inbox →
          </Link>
        </div>
      )}

      <div className="grid grid-cols-[1.6fr_1fr] gap-4">
        <div className="card">
          <div className="text-[14.5px] font-semibold mb-3.5">Connected accounts</div>
          {!accounts ? (
            <div className="text-textFaint text-[13px] py-4">Loading…</div>
          ) : accounts.length === 0 ? (
            <div className="text-textFaint text-[13px] py-4">No accounts connected yet.</div>
          ) : (
            accounts.map((a) => (
              <div key={a.id} className="flex items-center gap-3 py-3 border-b border-borderSoft last:border-0">
                <div className="w-8 h-8 rounded-full bg-surface3 flex items-center justify-center text-[12px] font-semibold text-textDim">
                  {a.provider[0].toUpperCase()}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="font-semibold text-[13px] truncate">{a.email_address}</div>
                  <div className="text-textFaint text-[12px] capitalize">{a.provider} · OAuth 2.0</div>
                </div>
                <button className="btn btn-primary btn-sm" onClick={() => sync(a.id)} disabled={busyId === a.id}>
                  {busyId === a.id ? <span className="spinner" /> : "Sync inbox"}
                </button>
                <button className="btn btn-ghost btn-sm" onClick={() => disconnect(a.id)}>
                  Disconnect
                </button>
              </div>
            ))
          )}
        </div>

        <div className="card">
          <div className="text-[14.5px] font-semibold mb-3.5">Add account</div>
          <button className="btn btn-ghost w-full justify-center mb-2" onClick={connectGmail} disabled={connecting}>
            {connecting ? <span className="spinner" /> : "+ Connect Gmail"}
          </button>
          <button className="btn btn-ghost w-full justify-center mb-2 opacity-50 cursor-not-allowed" disabled>
            + Outlook (coming soon)
          </button>
          <button className="btn btn-ghost w-full justify-center opacity-50 cursor-not-allowed" disabled>
            + IMAP / SMTP (coming soon)
          </button>
        </div>
      </div>
    </div>
  );
}

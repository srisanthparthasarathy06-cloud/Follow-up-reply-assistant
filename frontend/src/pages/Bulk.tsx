import { useEffect, useRef, useState } from "react";
import { useAuth } from "../context/AuthContext";
import { api } from "../lib/api";
import { BulkJobOut } from "../types";

export default function Bulk() {
  const { token } = useAuth();
  const [job, setJob] = useState<BulkJobOut | null>(null);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  function stopPolling() {
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = null;
  }

  async function poll(jobId: string) {
    if (!token) return;
    try {
      const j = await api.bulkStatus(token, jobId);
      setJob(j);
      if (j.status === "completed") stopPolling();
    } catch (e: any) {
      setError(e.message);
      stopPolling();
    }
  }

  async function start() {
    if (!token) return;
    setStarting(true);
    setError(null);
    try {
      const j = await api.bulkProcess(token, 1000);
      setJob(j);
      pollRef.current = setInterval(() => poll(j.id), 1500);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setStarting(false);
    }
  }

  async function retryFailed() {
    if (!token || !job) return;
    try {
      await api.bulkRetry(token, job.id);
      pollRef.current = setInterval(() => poll(job.id), 1500);
    } catch (e: any) {
      setError(e.message);
    }
  }

  useEffect(() => () => stopPolling(), []);

  const pct = job && job.total ? Math.round((job.processed / job.total) * 100) : 0;

  return (
    <div>
      <div className="mb-6">
        <div className="text-[22px] font-semibold font-display">Bulk processing</div>
        <div className="text-textDim text-[13px] mt-0.5">
          Runs asynchronously on the backend — this page just polls for progress.
        </div>
      </div>

      {error && <div className="bg-danger/10 text-danger text-[13px] px-3 py-2.5 rounded-lg mb-4">{error}</div>}

      <div className="card !p-6">
        <div className="flex justify-between items-center mb-0.5">
          <div className="text-[14.5px] font-semibold">Processing emails</div>
          <div className="font-mono text-textDim text-[13px]">{pct}%</div>
        </div>
        <div className="bg-surface2 h-2.5 rounded-full overflow-hidden my-3.5">
          <div
            className="h-full bg-gradient-to-r from-accent to-accent2 rounded-full transition-all"
            style={{ width: `${pct}%` }}
          />
        </div>
        <div className="flex justify-between text-[12.5px] text-textDim">
          <span>
            {job ? job.processed : 0} / {job ? job.total : 0}
          </span>
          <span>{job ? job.status : "Idle"}</span>
        </div>

        <div className="grid grid-cols-4 gap-3 mt-4.5">
          <div className="bg-surface2 rounded-lg px-3.5 py-3">
            <div className="font-display text-[19px] font-semibold">{job?.succeeded ?? 0}</div>
            <div className="text-[11.5px] text-textFaint mt-0.5">Successful</div>
          </div>
          <div className="bg-surface2 rounded-lg px-3.5 py-3">
            <div className="font-display text-[19px] font-semibold">{job?.failed ?? 0}</div>
            <div className="text-[11.5px] text-textFaint mt-0.5">Failed</div>
          </div>
          <div className="bg-surface2 rounded-lg px-3.5 py-3">
            <div className="font-display text-[19px] font-semibold">{job ? job.total - job.processed : 0}</div>
            <div className="text-[11.5px] text-textFaint mt-0.5">Remaining</div>
          </div>
          <div className="bg-surface2 rounded-lg px-3.5 py-3">
            <div className="font-display text-[19px] font-semibold">{job?.total ?? 0}</div>
            <div className="text-[11.5px] text-textFaint mt-0.5">Total in job</div>
          </div>
        </div>

        <div className="flex gap-2.5 mt-5">
          <button className="btn btn-primary" onClick={start} disabled={starting}>
            {starting ? <span className="spinner" /> : job?.status === "completed" ? "Run again" : "Process all pending emails"}
          </button>
          {job && job.failed > 0 && job.status === "completed" && (
            <button className="btn btn-ghost" onClick={retryFailed}>
              Retry failed
            </button>
          )}
        </div>

        {job && job.failed_email_ids.length > 0 && (
          <div className="mt-4.5 space-y-1.5">
            {job.failed_email_ids.map((id) => (
              <div key={id} className="flex justify-between items-center px-3 py-2 bg-danger/15 rounded-lg text-[12.5px]">
                <span>Email {id} could not be processed</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

import { useEffect, useState } from "react";
import { useAuth } from "../context/AuthContext";
import { api } from "../lib/api";
import { AnalyticsOut } from "../types";

export default function Analytics() {
  const { token } = useAuth();
  const [data, setData] = useState<AnalyticsOut | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;
    api
      .analytics(token)
      .then(setData)
      .catch((e) => setError(e.message));
  }, [token]);

  const days = data ? Object.entries(data.emails_processed_per_day).sort() : [];
  const max = Math.max(1, ...days.map(([, v]) => v));
  const topIntent = data ? Object.keys(data.top_intents)[0] : null;
  const topStyle = data ? Object.keys(data.top_reply_styles)[0] : null;

  return (
    <div>
      <div className="mb-6">
        <div className="text-[22px] font-semibold font-display">Analytics</div>
        <div className="text-textDim text-[13px] mt-0.5">Live stats from your backend.</div>
      </div>

      {error && <div className="bg-danger/10 text-danger text-[13px] px-3 py-2.5 rounded-lg mb-4">{error}</div>}

      <div className="grid grid-cols-4 gap-3.5 mb-4.5">
        <div className="card">
          <div className="font-display text-[22px] font-semibold">{data ? `${data.success_rate}%` : "–"}</div>
          <div className="text-textDim text-[12.5px] mt-1">Processing success rate</div>
        </div>
        <div className="card">
          <div className="font-display text-[22px] font-semibold">
            {data ? `${data.avg_processing_time_seconds.toFixed(1)}s` : "–"}
          </div>
          <div className="text-textDim text-[12.5px] mt-1">Avg. processing time / email</div>
        </div>
        <div className="card">
          <div className="font-display text-[22px] font-semibold">{topIntent || "–"}</div>
          <div className="text-textDim text-[12.5px] mt-1">Most common intent</div>
        </div>
        <div className="card">
          <div className="font-display text-[22px] font-semibold">{topStyle || "–"}</div>
          <div className="text-textDim text-[12.5px] mt-1">Most used reply style</div>
        </div>
      </div>

      <div className="card">
        <div className="text-[14.5px] font-semibold mb-4">Emails processed per day</div>
        <div className="flex items-end gap-2 h-[150px] relative mb-6">
          {days.length === 0 ? (
            <div className="text-textFaint text-[13px] w-full text-center self-center">No data yet.</div>
          ) : (
            days.map(([d, v]) => (
              <div
                key={d}
                className="flex-1 bg-gradient-to-b from-accent to-accent/25 rounded-t-[5px] relative min-h-[2px]"
                style={{ height: `${(v / max) * 100}%` }}
              >
                <div className="absolute -bottom-5 left-0 right-0 text-center text-[10.5px] text-textFaint">
                  {d.slice(5)}
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

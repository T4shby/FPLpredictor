import Link from "next/link";
import { fetchPicks, fetchStatus } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function HomePage() {
  let status = null;
  let picks: Awaited<ReturnType<typeof fetchPicks>> | null = null;
  let error = "";
  try {
    [status, picks] = await Promise.all([fetchStatus(), fetchPicks("B")]);
  } catch (err) {
    error = err instanceof Error ? err.message : "API unavailable";
  }

  return (
    <main>
      <h1>Gameweek {picks?.event_id ?? status?.next_gameweek ?? "—"}</h1>
      <p className="muted">
        {status ? (
          <>
            Season {status.season} · deadline {status.next_deadline ?? "unknown"} · data {status.data_status} · model {status.model_version}
          </>
        ) : (
          error || "Start the API with uvicorn, then refresh."
        )}
      </p>
      <p>
        Primary model is <strong>B (form + fixture)</strong>, which won 2025/26 MAE. Rankings exclude players projected under 1 minute.
      </p>
      <div className="grid">
        {(picks?.picks || []).slice(0, 12).map((pick) => (
          <article className="card" key={pick.category}>
            <h3>{pick.category}</h3>
            {pick.name ? (
              <>
                <strong>
                  <Link href={`/players/${pick.element}`}>{pick.name}</Link>
                </strong>
                <div className="muted">
                  {pick.team} · {pick.position} · £{pick.price?.toFixed(1)} · {pick.ownership}%
                </div>
                <div>GW {pick.xpts_gw?.toFixed(2)} · 3GW {pick.xpts_3gw?.toFixed(2)} · 5GW {pick.xpts_5gw?.toFixed(2)}</div>
              </>
            ) : (
              <div className="muted">n/a</div>
            )}
          </article>
        ))}
      </div>
      <p>
        <Link href="/rankings">Open full rankings →</Link>
      </p>
    </main>
  );
}

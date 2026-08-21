import Link from "next/link";
import { fetchPlayer } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function PlayerPage({ params }: { params: Promise<{ element: string }> }) {
  const { element } = await params;
  const id = Number(element);
  try {
    const player = await fetchPlayer(id, "B");
    const expl = player.explanation || {};
    const components = player.components || expl.components || {};
    return (
      <main>
        <p>
          <Link href="/rankings">← Rankings</Link>
        </p>
        <h1>{expl.name || `Player ${id}`}</h1>
        <p className="muted">
          {expl.team} · {expl.position}
        </p>
        <div className="grid">
          <article className="card">
            <h3>GW xPts</h3>
            <strong>{player.xpts_gw.toFixed(2)}</strong>
          </article>
          <article className="card">
            <h3>Next 3</h3>
            <strong>{(player.xpts_3gw ?? 0).toFixed(2)}</strong>
          </article>
          <article className="card">
            <h3>Next 5</h3>
            <strong>{(player.xpts_5gw ?? 0).toFixed(2)}</strong>
          </article>
          <article className="card">
            <h3>Expected minutes</h3>
            <strong>{(player.expected_minutes ?? 0).toFixed(0)}</strong>
            <div className="muted">start {(player.start_probability ?? 0).toFixed(2)}</div>
          </article>
        </div>
        <h2>Components</h2>
        <table>
          <tbody>
            {Object.entries(components).map(([key, value]) => (
              <tr key={key}>
                <td>{key}</td>
                <td className="num">{Number(value).toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="grid" style={{ marginTop: "1rem" }}>
          <article className="card">
            <h3>Positive</h3>
            <ul className="factors">
              {(expl.positives || []).map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </article>
          <article className="card">
            <h3>Negative</h3>
            <ul className="factors">
              {(expl.negatives || []).map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </article>
        </div>
      </main>
    );
  } catch (err) {
    return (
      <main>
        <h1>Player {id}</h1>
        <p className="muted">{err instanceof Error ? err.message : "Not found"}</p>
      </main>
    );
  }
}

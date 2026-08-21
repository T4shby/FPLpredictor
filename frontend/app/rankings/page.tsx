import Link from "next/link";
import { fetchRankings } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function RankingsPage({
  searchParams,
}: {
  searchParams: Promise<{ position?: string }>;
}) {
  const params = await searchParams;
  const position = params.position;
  let rows: Awaited<ReturnType<typeof fetchRankings>>["rows"] = [];
  let error = "";
  try {
    rows = (await fetchRankings("B", position)).rows;
  } catch (err) {
    error = err instanceof Error ? err.message : "API unavailable";
  }

  const filters = ["", "GKP", "DEF", "MID", "FWD"];
  return (
    <main>
      <h1>Rankings</h1>
      <p className="muted">Model B · sorted by GW xPts · {error || `${rows.length} players`}</p>
      <div className="filters">
        {filters.map((pos) => (
          <Link key={pos || "all"} href={pos ? `/rankings?position=${pos}` : "/rankings"} className={(!pos && !position) || pos === position ? "active" : ""}>
            {pos || "All"}
          </Link>
        ))}
      </div>
      <table>
        <thead>
          <tr>
            <th>#</th>
            <th>Player</th>
            <th>Team</th>
            <th>Pos</th>
            <th>Opp</th>
            <th className="num">Price</th>
            <th className="num">Own%</th>
            <th className="num">Mins</th>
            <th className="num">GW</th>
            <th className="num">3GW</th>
            <th className="num">5GW</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, idx) => (
            <tr key={row.element}>
              <td>{idx + 1}</td>
              <td>
                <Link href={`/players/${row.element}`}>{row.name || row.element}</Link>
              </td>
              <td>{row.team}</td>
              <td>{row.position}</td>
              <td>
                {row.was_home === true ? "(H) " : row.was_home === false ? "(A) " : ""}
                {row.opponent || ""}
              </td>
              <td className="num">{row.price != null ? `£${row.price.toFixed(1)}` : ""}</td>
              <td className="num">{row.ownership != null ? row.ownership.toFixed(1) : ""}</td>
              <td className="num">{row.expected_minutes?.toFixed(0)}</td>
              <td className="num">{row.xpts_gw?.toFixed(2)}</td>
              <td className="num">{row.xpts_3gw?.toFixed(2)}</td>
              <td className="num">{row.xpts_5gw?.toFixed(2)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </main>
  );
}

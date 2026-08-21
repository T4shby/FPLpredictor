import "./globals.css";
import Link from "next/link";

export const metadata = {
  title: "FPL Predictor",
  description: "Expected-points rankings from a leakage-safe walk-forward model",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="wrap">
          <header className="site">
            <div>
              <Link href="/">FPL Predictor</Link>
              <div className="muted">Model B xPts · 2026/27</div>
            </div>
            <nav>
              <Link href="/">Dashboard</Link>
              <Link href="/rankings">Rankings</Link>
            </nav>
          </header>
          {children}
        </div>
      </body>
    </html>
  );
}

#!/usr/bin/env python3
"""Ad-hoc visualisation: total logs and unique users per month.

Usage:
    source scripts/set-db-env-production.sh
    python scripts/adhoc_logs_per_month.py
"""

import os
import sys
from urllib.parse import quote_plus

import psycopg2
import psycopg2.extras

POWER_USER_THRESHOLD = 300

QUERY = """\
WITH user_totals AS (
    SELECT user_id, COUNT(*) AS lifetime_logs
    FROM tlog
    GROUP BY user_id
)
SELECT
    DATE_TRUNC('month', t.upd_timestamp)::date  AS month,
    COUNT(*)                                     AS total_logs,
    COUNT(DISTINCT t.user_id)                    AS unique_users,
    COUNT(DISTINCT t.user_id)
        FILTER (WHERE ut.lifetime_logs >= %(threshold)s)
                                                 AS power_users,
    COUNT(DISTINCT t.user_id)
        FILTER (WHERE ut.lifetime_logs < %(threshold)s)
                                                 AS regular_users
FROM tlog t
JOIN user_totals ut USING (user_id)
WHERE t.upd_timestamp >= '2025-01-01'
  AND t.upd_timestamp < DATE_TRUNC('month', CURRENT_DATE + INTERVAL '1 month')
GROUP BY 1
ORDER BY 1;
"""


def build_dsn() -> str:
    host = os.environ.get("DB_HOST", "")
    user = os.environ.get("DB_USER", "")
    if not (host and user):
        print(
            "Error: DB_HOST / DB_USER not set.\n"
            "  source scripts/set-db-env-production.sh",
            file=sys.stderr,
        )
        sys.exit(1)

    return (
        f"host={host} "
        f"port={os.environ.get('DB_PORT', '5432')} "
        f"dbname={os.environ.get('DB_NAME', '')} "
        f"user={user} "
        f"password={quote_plus(os.environ.get('DB_PASSWORD', ''))} "
        f"sslmode=require"
    )


def main() -> None:
    try:
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
        import matplotlib.ticker as ticker
    except ImportError:
        print(
            "matplotlib is required:  pip install matplotlib",
            file=sys.stderr,
        )
        sys.exit(1)

    print("Connecting to database...")
    conn = psycopg2.connect(build_dsn())
    try:
        with conn.cursor() as cur:
            cur.execute(QUERY, {"threshold": POWER_USER_THRESHOLD})
            rows = cur.fetchall()
    finally:
        conn.close()

    if not rows:
        print("No data returned.")
        sys.exit(0)

    months = [r[0] for r in rows]
    total_logs = [r[1] for r in rows]
    unique_users = [r[2] for r in rows]
    power_users = [r[3] for r in rows]
    regular_users = [r[4] for r in rows]

    print(f"Fetched {len(rows)} months of data "
          f"({months[0]:%b %Y} – {months[-1]:%b %Y})")

    fig, ax1 = plt.subplots(figsize=(14, 6))

    colour_logs = "#4c72b0"
    colour_power = "#c44e52"
    colour_regular = "#55a868"

    ax1.bar(months, total_logs, width=25, color=colour_logs, alpha=0.7,
            label="Total logs")
    ax1.set_xlabel("Month")
    ax1.set_ylabel("Total logs", color=colour_logs)
    ax1.tick_params(axis="y", labelcolor=colour_logs)
    ax1.yaxis.set_major_formatter(ticker.FuncFormatter(
        lambda x, _: f"{x:,.0f}"))

    ax2 = ax1.twinx()
    ax2.plot(months, power_users, color=colour_power, linewidth=2,
             marker="s", markersize=5,
             label=f"Power users ({POWER_USER_THRESHOLD}+ lifetime logs)")
    ax2.plot(months, regular_users, color=colour_regular, linewidth=2,
             marker="o", markersize=5,
             label=f"Regular users (<{POWER_USER_THRESHOLD} lifetime logs)")
    ax2.set_ylabel("Active users", color="black")
    ax2.tick_params(axis="y", labelcolor="black")
    ax2.yaxis.set_major_formatter(ticker.FuncFormatter(
        lambda x, _: f"{x:,.0f}"))

    ax1.xaxis.set_major_locator(mdates.MonthLocator())
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha="right")

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left")

    fig.suptitle("TrigpointingUK: Logs and Active Users per Month"
                 "\n(by date entered, not visit date)",
                 fontsize=14, fontweight="bold")
    fig.tight_layout()

    out_path = os.path.join(os.path.dirname(__file__),
                            "adhoc_logs_per_month.png")
    fig.savefig(out_path, dpi=150)
    print(f"Saved to {out_path}")
    plt.show()


if __name__ == "__main__":
    main()

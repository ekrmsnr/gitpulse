from __future__ import annotations

from pathlib import Path
from datetime import datetime

from .analyzer import RepoAnalyzer


_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
       background: #0d1117; color: #e6edf3; padding: 2rem; line-height: 1.6; }
h1 { font-size: 1.6rem; font-weight: 600; color: #f0f6fc; margin-bottom: .25rem; }
h2 { font-size: 1rem; font-weight: 600; color: #7d8590; margin: 2rem 0 .75rem;
     text-transform: uppercase; letter-spacing: .06em; }
.sub  { color: #7d8590; font-size: .875rem; margin-bottom: 2rem; }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
        gap: 12px; margin-bottom: 2rem; }
.card { background: #161b22; border: 1px solid #30363d; border-radius: 8px;
        padding: 1rem; }
.card .val { font-size: 1.4rem; font-weight: 600; color: #58a6ff; }
.card .lbl { font-size: .75rem; color: #7d8590; margin-top: 4px; }
table { width: 100%; border-collapse: collapse; margin-bottom: 2rem;
        background: #161b22; border-radius: 8px; overflow: hidden; }
th { text-align: left; padding: .5rem 1rem; color: #7d8590;
     font-size: .75rem; font-weight: 600; border-bottom: 1px solid #30363d; }
td { padding: .5rem 1rem; border-bottom: 1px solid #21262d; font-size: .875rem; }
tr:last-child td { border-bottom: none; }
.bar-wrap { display: flex; align-items: center; gap: 8px; }
.bar { height: 8px; border-radius: 4px; background: #1f6feb; min-width: 2px; }
.bar.green { background: #2ea043; }
.bar.yellow { background: #9e6a03; }
.pill { display: inline-block; padding: 2px 8px; border-radius: 12px;
        font-size: .75rem; font-weight: 500; }
.blue  { background: #1f3a5f; color: #58a6ff; }
.green { background: #12261e; color: #3fb950; }
.red   { background: #2d1118; color: #f85149; }
.spark { font-family: monospace; letter-spacing: 2px; color: #58a6ff; font-size: 1rem; }
"""


def build_html(output: Path, analyzer: RepoAnalyzer) -> None:
    summary = analyzer.summary()
    contributors = analyzer.top_contributors(15)
    churn = analyzer.top_churned_files(15)
    activity = analyzer.commit_activity()
    languages = analyzer.language_breakdown()

    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    repo_name = summary.get("repo_name", "unknown")

    # Summary cards
    cards_html = ""
    if summary.get("total_commits", 0) > 0:
        first: datetime = summary["first_commit"]
        last: datetime = summary["last_commit"]
        card_data = [
            ("Total commits", str(summary["total_commits"])),
            ("Contributors", str(summary["unique_authors"])),
            ("Branches", str(summary["branches"])),
            ("Active branch", summary["active_branch"]),
            ("First commit", first.strftime("%Y-%m-%d")),
            ("Last commit", last.strftime("%Y-%m-%d")),
            ("Repo age", f"{summary['age_days']} days"),
        ]
        for val, lbl in card_data:
            cards_html += f'<div class="card"><div class="val">{val}</div><div class="lbl">{lbl}</div></div>\n'

    # Contributors table
    max_commits = contributors[0]["commits"] if contributors else 1
    contrib_rows = ""
    for i, row in enumerate(contributors, 1):
        pct = int(row["commits"] / max_commits * 100)
        contrib_rows += f"""
        <tr>
          <td style="color:#7d8590">{i}</td>
          <td>{_esc(row['author'])}</td>
          <td><div class="bar-wrap"><div class="bar" style="width:{pct}%"></div>
              <span class="pill blue">{row['commits']}</span></div></td>
          <td><span class="pill green">+{row['additions']:,}</span></td>
          <td><span class="pill red">-{row['deletions']:,}</span></td>
        </tr>"""

    # Churn table
    max_churn = churn[0]["lines_changed"] if churn else 1
    churn_rows = ""
    for i, row in enumerate(churn, 1):
        pct = int(row["lines_changed"] / max_churn * 100)
        churn_rows += f"""
        <tr>
          <td style="color:#7d8590">{i}</td>
          <td style="font-family:monospace">{_esc(row['file'])}</td>
          <td><div class="bar-wrap">
              <div class="bar yellow" style="width:{max(pct,2)}%"></div>
              <span>{row['lines_changed']:,}</span></div></td>
        </tr>"""

    # Weekday bar chart
    weekday = activity["by_weekday"]
    max_wd = max(weekday.values()) if weekday else 1
    wd_html = ""
    for day, count in weekday.items():
        pct = int(count / max_wd * 100)
        wd_html += f"""
        <div style="display:flex;align-items:center;gap:12px;margin-bottom:6px">
          <span style="width:32px;color:#7d8590;font-size:.8rem">{day}</span>
          <div style="flex:1;background:#21262d;border-radius:4px;height:12px">
            <div style="width:{max(pct,1)}%;background:#1f6feb;height:12px;border-radius:4px"></div>
          </div>
          <span style="width:28px;text-align:right;font-size:.8rem">{count}</span>
        </div>"""

    # Sparkline
    by_hour = activity.get("by_hour", {})
    spark = ""
    if by_hour:
        max_h = max(by_hour.values()) if by_hour else 1
        levels = " ▁▂▃▄▅▆▇█"
        for h in range(24):
            v = by_hour.get(h, 0)
            idx = int(v / max_h * (len(levels) - 1))
            spark += levels[idx]

    # Languages
    lang_rows = ""
    for row in languages[:12]:
        pct = int(row["pct"])
        lang_rows += f"""
        <div style="display:flex;align-items:center;gap:12px;margin-bottom:8px">
          <span style="width:130px;font-size:.85rem">{_esc(row['language'])}</span>
          <div style="flex:1;background:#21262d;border-radius:4px;height:10px">
            <div style="width:{max(pct,1)}%;background:#2ea043;height:10px;border-radius:4px"></div>
          </div>
          <span style="width:40px;text-align:right;font-size:.8rem;color:#7d8590">{row['pct']}%</span>
        </div>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>gitpulse — {_esc(repo_name)}</title>
<style>{_CSS}</style>
</head>
<body>
  <h1>⚡ {_esc(repo_name)}</h1>
  <p class="sub">Generated by <strong>gitpulse</strong> · {now}</p>

  <h2>Summary</h2>
  <div class="grid">{cards_html}</div>

  <h2>Top contributors</h2>
  <table>
    <thead><tr><th>#</th><th>Author</th><th>Commits</th><th>Additions</th><th>Deletions</th></tr></thead>
    <tbody>{contrib_rows}</tbody>
  </table>

  <h2>Most changed files</h2>
  <table>
    <thead><tr><th>#</th><th>File</th><th>Lines changed</th></tr></thead>
    <tbody>{churn_rows}</tbody>
  </table>

  <h2>Commit activity</h2>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:2rem;margin-bottom:2rem">
    <div>
      <p style="font-size:.8rem;color:#7d8590;margin-bottom:.75rem">By day of week</p>
      {wd_html}
    </div>
    <div>
      <p style="font-size:.8rem;color:#7d8590;margin-bottom:.75rem">By hour (00–23)</p>
      <p class="spark">{spark}</p>
    </div>
  </div>

  <h2>Language breakdown</h2>
  <div style="max-width:480px">{lang_rows}</div>

  <p style="margin-top:3rem;color:#7d8590;font-size:.75rem">
    Made with <a href="https://github.com/ekrmsnr/gitpulse" style="color:#58a6ff">gitpulse</a>
  </p>
</body>
</html>"""

    output.write_text(html, encoding="utf-8")


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

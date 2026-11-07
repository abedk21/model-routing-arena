"""Self-contained accessible HTML report for the offline simulator."""
from __future__ import annotations
from html import escape


def render(results: list[dict]) -> str:
    rows = []
    charts = []
    for idx, r in enumerate(results):
        rows.append(f'<tr><th scope="row">{escape(r["policy"])}</th><td>{r["success_rate"]:.1%}</td>'
                    f'<td>${r["total_cost_usd"]:.4f}</td><td>{r["p95_latency_ms"]} ms</td>'
                    f'<td>{r["hindsight_regret"]:.2f}</td></tr>')
        bar_width = round(r["success_rate"] * 440, 1)
        y = 18 + idx * 78
        charts.append(f'<text x="0" y="{y}" class="svglabel">{escape(r["policy"])}</text>'
                      f'<rect x="0" y="{y+10}" width="440" height="28" rx="5" fill="#233348"/>'
                      f'<rect x="0" y="{y+10}" width="{bar_width}" height="28" rx="5" fill="{["#9de6b1", "#76c8ec", "#f8c782"][idx]}"/>'
                      f'<text x="450" y="{y+30}" class="svgpercent">{r["success_rate"]:.1%}</text>')
    details = ''.join('<details><summary>'+escape(r['policy'])+' · decisions</summary><div class="scroll"><table><thead><tr><th>Task</th><th>Kind</th><th>Risk</th><th>Selected model</th><th>Result</th><th>Latency</th></tr></thead><tbody>'+''.join(
        '<tr><td>'+escape(o['task_id'])+'</td><td>'+escape(o['kind'])+'</td><td>'+escape(o['risk'])+'</td><td>'+escape(o['model'])+'</td><td>'+('Success' if o['success'] else 'Failed')+'</td><td>'+str(o['latency_ms'])+' ms</td></tr>' for o in r['outcomes'])+'</tbody></table></div></details>' for r in results)
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Model Routing Arena · Experiment Report</title><style>
:root{{color-scheme:dark}}*{{box-sizing:border-box}}body{{margin:0;background:#0b1525;color:#e8eef8;font:16px/1.55 system-ui,-apple-system,Segoe UI,sans-serif}}main{{max-width:1050px;margin:auto;padding:clamp(20px,5vw,64px)}}.eyebrow{{font-weight:700;text-transform:uppercase;letter-spacing:.18em;color:#9de6b1;font-size:.77rem}}h1{{font-size:clamp(2rem,5vw,3.7rem);line-height:1.1;margin:12px 0 16px}}h2{{margin-top:44px}}p{{color:#bac9dc;max-width:68ch}}.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin:32px 0}}.card{{background:#15263a;border:1px solid #33455d;padding:22px;border-radius:14px}}.number{{font-size:1.9rem;font-weight:800;display:block}}.muted{{color:#afc1d7;font-size:.9rem}}.panel{{background:#102035;border-radius:16px;padding:24px;border:1px solid #344962;margin-top:18px}}table{{width:100%;border-collapse:collapse;text-align:left}}th,td{{padding:12px 14px;border-bottom:1px solid #33465d}}td{{font-variant-numeric:tabular-nums}}th{{color:#daf0fa}}.scroll{{overflow:auto}}svg{{width:100%;height:auto;max-width:560px}}.svglabel{{fill:#dfe8f3;font-size:15px}}.svgpercent{{fill:#dfe8f3;font-size:16px}}details{{border-top:1px solid #33465d;padding:14px 0}}summary{{cursor:pointer;font-weight:650}}footer{{font-size:.85rem;margin-top:36px;color:#a6b9cc}}a{{color:#9de6b1}}@media(max-width:560px){{th,td{{padding:8px}}}}</style></head><body><main>
<div class="eyebrow">Offline evaluation / seeded simulation</div><h1>Model Routing Arena</h1><p>Three routing strategies enter the arena. A deterministic mock benchmark measures which model each policy selects for synthetic tasks. The results are not real LLM performance.</p>
<div class="cards"><div class="card"><span class="muted">Simulated requests</span><span class="number">{results[0]['count']}</span></div><div class="card"><span class="muted">Random seed</span><span class="number">{results[0]['seed']}</span></div><div class="card"><span class="muted">Routing policies</span><span class="number">{len(results)}</span></div></div>
<section class="panel"><h2>Outcome comparison</h2><div class="scroll"><table><thead><tr><th>Strategy</th><th>Success</th><th>Mock cost</th><th>P95 latency</th><th>Hindsight regret</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div></section>
<section class="panel"><h2>Simulated success rate</h2><svg role="img" aria-label="Bar chart of success rates by routing policy" viewBox="0 0 560 255">{''.join(charts)}</svg></section>
<section class="panel"><h2>Decision trace</h2><p>Expand a policy to inspect every request and selected model.</p>{details}</section>
<footer>All scores, costs, latency estimates and policy outcomes are illustrative. Hindsight regret assumes impossible after-the-fact knowledge of every model result; it is a diagnostic comparator, not a deployable oracle. No provider APIs are used.</footer></main></body></html>'''

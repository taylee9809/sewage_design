"""간선 종단 비교 그림. 사용: py -3 -m engine.plot_profile SYN01 docs/SYN01_trunk_profile.png"""
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import psycopg  # noqa: E402

from engine.design import run  # noqa: E402
from engine.network import load_network  # noqa: E402

plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False
PALETTE = ["#1f4e79", "#c0504d", "#4f9a4f", "#e08a00", "#8064a2", "#2a9d8f", "#6d6d6d"]


def main(pid, out_png, trunk_prefix="T"):
    with psycopg.connect(os.environ["SEWAGE_DB_DSN"]) as con, con.cursor() as cur:
        nodes, links = load_network(cur, pid)
    L = {l["id"]: l for l in links}
    trunk = sorted(k for k in L if k.startswith(trunk_prefix))
    fig, (ax, ax2) = plt.subplots(2, 1, figsize=(12, 8), gridspec_kw={"height_ratios": [3, 1]}, sharex=True)
    xs, gl = [0], [nodes[L[trunk[0]]["up"]]["gl"]]
    for t in trunk:
        xs.append(xs[-1] + L[t]["L"])
        gl.append(nodes[L[t]["dn"]]["gl"])
    ax.plot(xs, gl, color="#666", lw=2, label="지반고")
    results = run(pid)
    with psycopg.connect(os.environ["SEWAGE_DB_DSN"]) as con, con.cursor() as cur:
        cur.execute("SELECT standard_id, title, edition FROM criteria.standard")
        names = {a: "%s (%s)" % (a, c) for a, b, c in cur.fetchall()}
    n = len(results)
    for k, (sid, outl) in enumerate(results.items()):
        color = PALETTE[k % len(PALETTE)]
        res = {o["link"]: o for o in outl}
        x = 0
        for i, t in enumerate(trunk):
            o = res[t]
            x2 = x + o["L"]
            ax.plot([x, x2], [o["inv_up"], o["inv_dn"]], color=color, lw=1.8, label=names.get(sid, sid) if i == 0 else None)
            ax2.bar((x + x2) / 2 + (k - (n - 1) / 2) * 8, o["dia"], width=8, color=color)
            x = x2
    ax.set_ylabel("표고 (m) — 선: 관저고")
    ax.legend()
    ax.grid(alpha=.3)
    ax.set_title("%s 간선 종단 비교 (같은 관망·같은 인구, 각국 기준 원문 규칙, 각국 PVC 관 규격 내경)" % pid)
    ax2.set_ylabel("호칭경 (mm)")
    ax2.set_xlabel("간선 누가거리 (m)")
    ax2.grid(alpha=.3)
    fig.tight_layout()
    fig.savefig(out_png, dpi=120)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])

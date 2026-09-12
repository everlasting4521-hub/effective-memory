from __future__ import annotations
from pathlib import Path
from datetime import datetime
import json
import pandas as pd
import streamlit as st

BASE = Path(__file__).resolve().parent
SNAP = BASE / "cloud_data" / "latest.json"

st.set_page_config(page_title="chai1号", layout="centered")

st.markdown("""
<style>
.block-container{padding-top:1.5rem;max-width:850px}
.title{font-size:2.2rem;font-weight:800;line-height:1.35;margin:.4rem 0}
.card{border:1px solid rgba(128,128,128,.35);border-radius:.8rem;padding:1rem;margin:.7rem 0}
.hot{border:2px solid rgba(255,90,70,.75);border-radius:.8rem;padding:1rem;margin:.7rem 0}
.small{opacity:.72;font-size:.9rem}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="title">🏇 競馬予想AI（chai1号）</div>', unsafe_allow_html=True)

if not SNAP.exists():
    st.warning("クラウド用予想データはまだありません。")
    st.stop()

try:
    data = json.loads(SNAP.read_text(encoding="utf-8"))
except Exception as e:
    st.error(f"データ読込エラー: {e}")
    st.stop()

status = data.get("data_status", "STALE")
gen = data.get("generated_at", "-")
last = data.get("last_update", "-")
date = str(data.get("date", ""))

c1, c2 = st.columns(2)
c1.metric("データ", "🟢 LIVE" if status == "LIVE" else "🟡 最終保存")
c2.metric("最終更新", last)
st.caption(f"{date} / snapshot {gen}")

st.markdown("## 🔥 本日の勝負レース")
picks = data.get("battle_picks") or data.get("official_picks") or []

if not picks:
    st.info("現在、S級/A級の勝負レースはありません。今日は見送りです。")
else:
    for i, p in enumerate(picks[:3]):
        grade = p.get("判定", "候補")
        rid = str(p.get("race_id", ""))
        horse_no = p.get("馬番", "")
        horse = p.get("馬名", "")
        start = p.get("発走時刻", "-")
        maxev = p.get("最大EV")
        cls = "hot" if i == 0 else "card"
        title = f"🔥 最優先・{grade}" if i == 0 else f"{grade}・候補{i+1}"
        evtxt = "-" if maxev in (None, "") else f"{float(maxev):.2f}"

        st.markdown(
            f'<div class="{cls}"><b>{title}</b><br>{rid}<br>'
            f'発走 {start} ／ 推奨 {horse_no}番 {horse} ／ 最大EV {evtxt}</div>',
            unsafe_allow_html=True
        )

        plan = p.get("購入プラン") or []
        if plan:
            df = pd.DataFrame(plan)
            keep = [c for c in ["券種","馬番","馬名","AI確率","オッズ","EV","購入額"] if c in df.columns]
            if "AI確率" in df.columns:
                df["AI確率"] = pd.to_numeric(df["AI確率"], errors="coerce") * 100
            st.dataframe(df[keep], use_container_width=True, hide_index=True)
            total = pd.to_numeric(df.get("購入額", pd.Series(dtype=float)), errors="coerce").fillna(0).sum()
            st.success(f"2,000円で買うなら：合計 {int(total):,}円")
        else:
            st.caption("買い目詳細は次回同期時に更新されます。")

        reason = p.get("理由")
        if reason:
            st.caption(f"選定理由：{reason}")

st.markdown("## 🌤 馬場")
conds = data.get("conditions") or []
if conds:
    for c in conds:
        venue = c.get("場所", "")
        weather = c.get("天候", "-")
        turf = c.get("芝馬場", "-")
        dirt = c.get("ダート馬場", "-")
        st.write(f"**{venue}**　天候 {weather} ／ 芝 {turf} ／ ダート {dirt}")
else:
    st.caption("馬場情報未取得")

st.divider()
st.caption("chai1号はS級/A級が無ければ買いません。トラックバイアス・当日好走血統は使用しません。")

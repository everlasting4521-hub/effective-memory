from pathlib import Path
from datetime import datetime, timezone, timedelta
import json
import pandas as pd
import streamlit as st

BASE = Path(__file__).resolve().parent
CLOUD = BASE / "cloud_data"
INDEX = CLOUD / "upcoming_meetings.json"
JST = timezone(timedelta(hours=9))

st.set_page_config(page_title="chai1号", layout="centered")

st.markdown("""
<style>
.block-container{padding-top:1.3rem;max-width:900px}
.title{font-size:2.15rem;font-weight:800;line-height:1.35;margin:.35rem 0}
.card{border:1px solid rgba(128,128,128,.35);border-radius:.8rem;padding:1rem;margin:.7rem 0}
.hot{border:2px solid rgba(255,90,70,.75);border-radius:.8rem;padding:1rem;margin:.7rem 0}
.small{opacity:.75;font-size:.92rem}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="title">🏇 競馬予想AI（chai1号）</div>', unsafe_allow_html=True)

if not INDEX.exists():
    st.warning("開催日データがまだありません。")
    st.stop()

idx = json.loads(INDEX.read_text(encoding="utf-8-sig"))
meeting_days = [str(x.get("date","")) for x in idx.get("meeting_days",[]) if x.get("date")]

# v31.9: 実際にクラウドへ保存されている日付も候補へ追加
for p in CLOUD.glob("day_*.json"):
    d = p.stem.replace("day_", "", 1)
    if d.isdigit() and len(d) == 8:
        meeting_days.append(d)

for p in CLOUD.glob("snapshot_*.json"):
    d = p.stem.replace("snapshot_", "", 1)
    if d.isdigit() and len(d) == 8:
        meeting_days.append(d)

latest_path = CLOUD / "latest.json"
if latest_path.exists():
    try:
        latest_meta = json.loads(latest_path.read_text(encoding="utf-8-sig"))
        latest_date = str(latest_meta.get("date", "")).strip()
        if latest_date.isdigit() and len(latest_date) == 8:
            meeting_days.append(latest_date)
    except Exception:
        pass

meeting_days = sorted(set(meeting_days))

if not meeting_days:
    st.warning("開催日が登録されていません。")
    st.stop()

now_jst = datetime.now(JST)
today = now_jst.strftime("%Y%m%d")

def choose_default(days, today):
    if today in days:
        return days.index(today)
    future = [d for d in days if d > today]
    if future:
        return days.index(sorted(future)[0])
    return len(days) - 1

def label_date(d):
    dt = datetime.strptime(d, "%Y%m%d")
    s = dt.strftime("%Y/%m/%d")
    if d == today:
        s += "（今日）"
    return s

selected_date = st.selectbox(
    "開催日",
    meeting_days,
    index=choose_default(meeting_days, today),
    format_func=label_date,
)

# v31.9: day → snapshot → latest の順で読み込む
candidates = [
    CLOUD / f"day_{selected_date}.json",
    CLOUD / f"snapshot_{selected_date}.json",
]

snap_path = next((p for p in candidates if p.exists()), None)

if snap_path is not None:
    data = json.loads(snap_path.read_text(encoding="utf-8-sig"))
else:
    latest_path = CLOUD / "latest.json"

    if latest_path.exists():
        latest_data = json.loads(
            latest_path.read_text(encoding="utf-8-sig")
        )

        if str(latest_data.get("date", "")).strip() == selected_date:
            data = latest_data
        else:
            data = None
    else:
        data = None

    if data is None:
        st.warning(f"{label_date(selected_date)} のクラウドデータがありません。")
        st.stop()

gen = data.get("generated_at", "")
last = data.get("last_update", "-")
if not last or last == "-":
    if gen:
        try:
            # generated_at はPC側JSTのnaive時刻として保存されるため、そのまま表示時刻に使用
            last = datetime.fromisoformat(gen).strftime("%H:%M:%S")
        except Exception:
            last = gen
    else:
        last = "-"

age_min = None
try:
    g = datetime.fromisoformat(gen)
    if g.tzinfo is None:
        g = g.replace(tzinfo=JST)
    else:
        g = g.astimezone(JST)
    age_min = max((now_jst - g).total_seconds()/60, 0)
except Exception:
    pass

is_live = (selected_date == today and age_min is not None and age_min <= 20)

c1, c2 = st.columns(2)

if data.get("meeting") is False or data.get("data_status") == "NO_MEETING":
    data_label = "⚪ 非開催日"
elif is_live:
    data_label = "🟢 LIVE"
else:
    data_label = "📦 保存データ"

c1.metric("データ", data_label)
c2.metric("最終更新", last)

if age_min is not None and selected_date == today:
    st.caption(f"{label_date(selected_date)} / 約{age_min:.0f}分前に同期")
else:
    st.caption(f"{label_date(selected_date)} の予想データ")

no_meeting = (
    data.get("meeting") is False
    or data.get("data_status") == "NO_MEETING"
)

if no_meeting:
    st.markdown("## 🏇 本日はJRA開催なし")
    st.info("本日は中央競馬の開催がありません。予想・オッズ更新・買い目生成は行いません。")
    st.caption("次の開催日は自動取得後、この画面に表示されます。")
    st.stop()
heading = "🔥 本日の勝負レース" if selected_date == today else "📅 選択日の勝負レース"
st.markdown(f"## {heading}")

picks = data.get("battle_picks") or data.get("official_picks") or []

if not picks:
    st.info("現在、S級/A級の勝負レースはありません。無理に買いません。")
else:
    for i, p in enumerate(picks[:3]):
        grade = p.get("判定", "候補")
        rid = str(p.get("race_id", ""))
        horse_no = p.get("馬番", "")
        horse = p.get("馬名", "")
        start = p.get("発走時刻", "-")
        maxev = p.get("最大EV")
        try:
            evtxt = f"{float(maxev):.2f}"
        except Exception:
            evtxt = "-"

        cls = "hot" if i == 0 else "card"
        title = f"🔥 最優先・{grade}" if i == 0 else f"{grade}・候補{i+1}"
        st.markdown(
            f'<div class="{cls}"><b>{title}</b><br>{rid}<br>'
            f'発走 {start} ／ 推奨 {horse_no}番 {horse} ／ 最大EV {evtxt}</div>',
            unsafe_allow_html=True,
        )

        plan = p.get("購入プラン") or []
        if plan:
            df = pd.DataFrame(plan)
            keep = [c for c in ["券種","馬番","馬名","AI確率","オッズ","EV","購入額"] if c in df.columns]
            if "AI確率" in df.columns:
                prob = pd.to_numeric(df["AI確率"], errors="coerce")
                if prob.max(skipna=True) <= 1.0:
                    df["AI確率"] = prob * 100
                else:
                    df["AI確率"] = prob
            st.dataframe(df[keep], use_container_width=True, hide_index=True)

            total = pd.to_numeric(df.get("購入額", pd.Series(dtype=float)), errors="coerce").fillna(0).sum()
            st.success(f"2,000円で買うなら：合計 {int(total):,}円")

        if p.get("理由"):
            st.caption(f"選定理由：{p.get('理由')}")

st.markdown("## 🌤 馬場")
conds = data.get("conditions") or []
if conds:
    for c in conds:
        st.write(
            f"**{c.get('場所','')}**　"
            f"天候 {c.get('天候','-')} ／ 芝 {c.get('芝馬場','-')} ／ ダート {c.get('ダート馬場','-')}"
        )
else:
    st.caption("馬場情報未取得")

st.divider()
st.caption("S級/A級が無ければ買いません。1レース2,000円固定。トラックバイアス・当日好走血統は使用しません。")

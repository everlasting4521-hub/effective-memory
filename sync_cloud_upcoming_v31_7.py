# -*- coding: utf-8 -*-
"""
chai1号 v31.7
開催2日分をCloudへ同期し、JST基準で active day を決定する。
"""
from __future__ import annotations
import argparse, json, shutil, subprocess, sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

BASE = Path(__file__).resolve().parent
DATA = BASE / "data" / "daily"
CLOUD = BASE / "cloud_data"
PYTHON = sys.executable
JST = timezone(timedelta(hours=9))

def run(cmd):
    return subprocess.run(cmd, cwd=BASE, text=True, capture_output=True,
                          encoding="utf-8", errors="replace")

def load_meetings():
    p = DATA / "upcoming_meetings.json"
    if not p.exists():
        return []
    try:
        obj = json.loads(p.read_text(encoding="utf-8-sig"))
    except Exception:
        return []
    out = []
    for x in obj.get("meeting_days", []):
        d = str(x.get("date","")).strip()
        if len(d)==8 and d.isdigit():
            out.append({"date": d, "races": int(x.get("races",0) or 0)})
    return out

def choose_active(dates, today):
    if today in dates:
        return today
    future = sorted([d for d in dates if d > today])
    if future:
        return future[0]
    return sorted(dates)[-1] if dates else today

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=datetime.now(JST).strftime("%Y%m%d"))
    args = ap.parse_args()

    CLOUD.mkdir(parents=True, exist_ok=True)
    meetings = load_meetings()
    if not meetings:
        print("[CLOUD JST] no upcoming meetings")
        return 1

    builder = BASE / "build_cloud_snapshot_v31_2.py"
    if not builder.exists():
        print("[CLOUD JST] builder missing")
        return 1

    built = []
    for item in meetings[:2]:
        d = item["date"]
        p = run([PYTHON, str(builder), "--date", d])
        if p.returncode != 0:
            print(f"[CLOUD JST] build failed {d}")
            continue
        latest = CLOUD / "latest.json"
        if not latest.exists():
            continue
        shutil.copy2(latest, CLOUD / f"day_{d}.json")
        built.append(d)
        print(f"[CLOUD JST] built day_{d}.json")

    if not built:
        return 1

    index = {
        "generated_at": datetime.now(JST).isoformat(timespec="seconds"),
        "timezone": "Asia/Tokyo",
        "meeting_days": [x for x in meetings if x["date"] in built],
    }
    (CLOUD/"upcoming_meetings.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8-sig"
    )

    active = choose_active(built, args.date)
    shutil.copy2(CLOUD/f"day_{active}.json", CLOUD/"latest.json")
    print(f"[CLOUD JST] active={active}")

    files = ["cloud_data/latest.json","cloud_data/upcoming_meetings.json"] + \
            [f"cloud_data/day_{d}.json" for d in built]

    if run(["git","add",*files]).returncode != 0:
        return 1

    if run(["git","diff","--cached","--quiet","--",*files]).returncode == 0:
        print("[CLOUD JST] no changes")
        return 0

    msg = f"Auto update chai1 JST {datetime.now(JST):%Y-%m-%d %H:%M:%S}"
    if run(["git","commit","-m",msg,"--",*files]).returncode != 0:
        return 1
    p = run(["git","push","origin","main"])
    if p.returncode != 0:
        print((p.stderr or p.stdout)[-1000:])
        return 1

    print(f"[CLOUD JST] OK {datetime.now(JST):%H:%M:%S}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

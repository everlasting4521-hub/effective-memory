# -*- coding: utf-8 -*-
"""
chai1号 v31.6
開催日2日分を Cloud に公開する同期スクリプト。

流れ:
1. data/daily/upcoming_meetings.json を読む
2. 各開催日について build_cloud_snapshot_v31_2.py --date YYYYMMDD を実行
3. 生成された cloud_data/latest.json を cloud_data/day_YYYYMMDD.json として保存
4. cloud_data/upcoming_meetings.json を更新
5. 今日が開催日なら今日、そうでなければ直近開催日を latest.json にする
6. GitHub に必要ファイルだけ commit/push
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent
DATA = BASE / "data" / "daily"
CLOUD = BASE / "cloud_data"
PYTHON = sys.executable


def run(cmd):
    return subprocess.run(
        cmd,
        cwd=BASE,
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )


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
        d = str(x.get("date", "")).strip()
        if len(d) == 8 and d.isdigit():
            out.append({"date": d, "races": int(x.get("races", 0) or 0)})
    return out


def choose_active(dates, today):
    if today in dates:
        return today
    future = sorted([d for d in dates if d >= today])
    if future:
        return future[0]
    return sorted(dates)[-1] if dates else today


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=datetime.now().strftime("%Y%m%d"))
    args = ap.parse_args()
    today = args.date

    CLOUD.mkdir(parents=True, exist_ok=True)

    meetings = load_meetings()
    if not meetings:
        print("[CLOUD2] upcoming_meetings.json is empty")
        return 1

    built = []
    builder = BASE / "build_cloud_snapshot_v31_2.py"
    if not builder.exists():
        print("[CLOUD2] build_cloud_snapshot_v31_2.py not found")
        return 1

    for item in meetings[:2]:
        d = item["date"]
        p = run([PYTHON, str(builder), "--date", d])
        if p.returncode != 0:
            print(f"[CLOUD2] build failed: {d}")
            print((p.stderr or p.stdout)[-1000:])
            continue

        latest = CLOUD / "latest.json"
        if not latest.exists():
            print(f"[CLOUD2] latest.json missing after build: {d}")
            continue

        dest = CLOUD / f"day_{d}.json"
        shutil.copy2(latest, dest)
        built.append(d)
        print(f"[CLOUD2] built {dest.name}")

    if not built:
        print("[CLOUD2] no day snapshots built")
        return 1

    index = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "meeting_days": [x for x in meetings if x["date"] in built],
    }
    (CLOUD / "upcoming_meetings.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2),
        encoding="utf-8-sig",
    )

    active = choose_active(built, today)
    shutil.copy2(CLOUD / f"day_{active}.json", CLOUD / "latest.json")
    print(f"[CLOUD2] active={active}")

    # Git: Cloudに必要なファイルだけ
    git_files = [
        "cloud_data/latest.json",
        "cloud_data/upcoming_meetings.json",
    ] + [f"cloud_data/day_{d}.json" for d in built]

    p = run(["git", "add", *git_files])
    if p.returncode != 0:
        print("[CLOUD2] git add ERROR")
        print((p.stderr or p.stdout)[-1000:])
        return 1

    diff = run(["git", "diff", "--cached", "--quiet", "--", *git_files])
    if diff.returncode == 0:
        print("[CLOUD2] no changes")
        return 0

    msg = f"Auto update chai1 upcoming {datetime.now():%Y-%m-%d %H:%M:%S}"
    p = run(["git", "commit", "-m", msg, "--", *git_files])
    if p.returncode != 0:
        print("[CLOUD2] commit ERROR")
        print((p.stderr or p.stdout)[-1000:])
        return 1

    p = run(["git", "push", "origin", "main"])
    if p.returncode != 0:
        print("[CLOUD2] push ERROR")
        print((p.stderr or p.stdout)[-1200:])
        return 1

    print(f"[CLOUD2] OK {datetime.now():%H:%M:%S}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

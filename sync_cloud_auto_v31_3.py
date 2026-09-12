from __future__ import annotations
import argparse, subprocess, sys
from datetime import datetime
from pathlib import Path

BASE=Path(__file__).resolve().parent
PYTHON=sys.executable

def run(cmd):
    return subprocess.run(cmd,cwd=BASE,text=True,capture_output=True,encoding="utf-8",errors="replace")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--date",default=datetime.now().strftime("%Y%m%d"))
    args=ap.parse_args()
    date=args.date

    p=run([PYTHON,str(BASE/"build_cloud_snapshot_v31_2.py"),"--date",date])
    if p.returncode!=0:
        print("cloud sync: snapshot build failed")
        return 1

    latest=BASE/"cloud_data"/"latest.json"
    if not latest.exists():
        print("cloud sync: latest.json not found")
        return 1

    if run(["git","rev-parse","--is-inside-work-tree"]).returncode!=0:
        print("cloud sync: git repository not available")
        return 1

    if run(["git","add","cloud_data/latest.json"]).returncode!=0:
        print("cloud sync: git add failed")
        return 1

    if run(["git","diff","--cached","--quiet"]).returncode==0:
        print("cloud sync: no changes")
        return 0

    msg=f"Auto update chai1 {date} {datetime.now():%H%M%S}"
    if run(["git","commit","-m",msg]).returncode!=0:
        print("cloud sync: git commit failed")
        return 1

    p=run(["git","push","origin","main"])
    if p.returncode!=0:
        print("cloud sync: git push failed")
        print((p.stderr or "")[-1200:])
        return 1

    print(f"cloud sync: OK {datetime.now():%H:%M:%S}")
    return 0

if __name__=="__main__":
    raise SystemExit(main())

from __future__ import annotations
import argparse,json,re,subprocess,sys,time,os
from datetime import datetime,timedelta
from pathlib import Path
import pandas as pd

BASE=Path(__file__).resolve().parent
DATA=BASE/"data"/"daily"
PYTHON=sys.executable

def write_status(date,**kwargs):
    p=DATA/f"auto_status_{date}.json"; cur={}
    if p.exists():
        try: cur=json.loads(p.read_text(encoding="utf-8-sig"))
        except Exception: pass
    cur.update(kwargs); cur["updated_at"]=datetime.now().isoformat(timespec="seconds")
    p.write_text(json.dumps(cur,ensure_ascii=False,indent=2),encoding="utf-8-sig")

def parse_hhmm(v):
    if pd.isna(v): return None
    d=re.sub(r"\D","",str(v))
    if len(d)==3:d="0"+d
    if len(d)>=4:
        h,m=int(d[-4:-2]),int(d[-2:])
        if 0<=h<=23 and 0<=m<=59:return h,m

def load_races(date):
    p=DATA/f"racecard_{date}.csv"
    if not p.exists(): return []
    try: df=pd.read_csv(p,encoding="utf-8-sig")
    except Exception:return []
    if "race_id" not in df.columns:return []
    tc=next((c for c in ["発走時刻","発走時刻_HHMM","start_time","発走","発走時間","発走予定時刻"] if c in df.columns),None)
    if not tc:return []
    day=datetime.strptime(date,"%Y%m%d"); out=[]
    for rid,g in df.groupby("race_id",sort=False):
        hm=parse_hhmm(g.iloc[0][tc])
        if hm: out.append((str(rid),day.replace(hour=hm[0],minute=hm[1],second=0,microsecond=0)))
    return sorted(out,key=lambda x:x[1])

def completed(date):
    p=DATA/f"live_results_{date}.csv"
    if not p.exists(): return set()
    try:df=pd.read_csv(p,encoding="utf-8-sig")
    except Exception:return set()
    if "race_id" not in df.columns or "確定着順" not in df.columns:return set()
    pos=pd.to_numeric(df["確定着順"],errors="coerce")
    return set(df.loc[pos.eq(1),"race_id"].dropna().astype(str))

def next_race(date):
    now=datetime.now(); done=completed(date)
    cand=[x for x in load_races(date) if x[0] not in done and x[1]>=now-timedelta(minutes=10)]
    return cand[0] if cand else (None,None)

def interval(dt):
    if dt is None:return 600
    m=(dt-datetime.now()).total_seconds()/60
    if m>60:return 900
    if m>30:return 600
    if m>15:return 300
    if m>5:return 120
    if m>-5:return 60
    return 180

def run_script(name,date):
    return subprocess.run([PYTHON,str(BASE/name),"--date",date],cwd=BASE).returncode

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--date",default=datetime.now().strftime("%Y%m%d"))
    ap.add_argument("--skip-initial-full",action="store_true")
    args=ap.parse_args(); date=args.date
    DATA.mkdir(parents=True,exist_ok=True)
    stop=DATA/f"auto_stop_{date}.flag"; stop.unlink(missing_ok=True)
    pid=DATA/f"auto_driver_{date}.pid"; pid.write_text(str(os.getpid()),encoding="ascii")
    write_status(date,running=True,state="起動中",cloud_sync="-",last_success="-",next_check="-",next_race="-")

    if not args.skip_initial_full:
        rc=run_script("update_daily_auto_v31.py",date)
        if rc!=0:
            write_status(date,running=False,state="初回フル更新エラー")
            raise SystemExit(rc)

    run_script("build_battle_snapshot_v31_1.py",date)
    run_script("sync_cloud_auto_v31_3.py",date)

    try:
        while True:
            if stop.exists():
                write_status(date,running=False,state="停止指示"); break

            live_rc=run_script("update_live_v31.py",date)
            battle_rc=run_script("build_battle_snapshot_v31_1.py",date)
            cloud_rc=run_script("sync_cloud_auto_v31_3.py",date)

            subprocess.run([PYTHON,str(BASE/"audit_live_v30.py"),"--date",date],cwd=BASE)

            now=datetime.now(); rid,dt=next_race(date); sec=interval(dt)
            write_status(
                date,running=True,
                state="監視中" if live_rc==0 and battle_rc==0 else "更新エラー",
                last_success=now.strftime("%H:%M:%S") if live_rc==0 else f"ERROR {now:%H:%M:%S}",
                cloud_sync="正常" if cloud_rc==0 else "同期エラー",
                cloud_sync_at=now.strftime("%H:%M:%S"),
                next_check=(datetime.now()+timedelta(seconds=sec)).strftime("%H:%M:%S"),
                next_race=rid or "本日終了/未取得",
                next_start=dt.strftime("%H:%M") if dt else "-",
                interval_seconds=sec
            )

            if datetime.now().strftime("%Y%m%d")!=date:
                write_status(date,running=False,state="日付変更で終了"); break
            time.sleep(sec)
    finally:
        pid.unlink(missing_ok=True)

if __name__=="__main__":
    main()

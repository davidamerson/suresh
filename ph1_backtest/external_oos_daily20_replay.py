import json
from pathlib import Path
import pandas as pd
import requests

URL='https://raw.githubusercontent.com/TanvirCCC/algo-trading/main/backtest/lnterqo_v3_oos_trades.csv'
START=1000.0; TARGET=20.0; WITHDRAW=10.0

def load():
    r=requests.get(URL,timeout=60); r.raise_for_status(); Path('/tmp/oos.csv').write_bytes(r.content)
    d=pd.read_csv('/tmp/oos.csv'); d['entry_time']=pd.to_datetime(d['entry_time']); d=d.sort_values('entry_time').reset_index(drop=True); return d

def replay(d,start,end):
    x=d[(d.entry_time>=pd.Timestamp(start))&(d.entry_time<=pd.Timestamp(end))].copy()
    bal=START; wd=0.; peak=START; maxdd=0.; cur=None; dayp=0.; daily_loss=0.; cons=0; nday=0; stopped=False
    targets=0; taken=0; skipped=0; wins=0; losses=0; daily=[]; anomalies=0
    for _,r in x.iterrows():
        day=r.entry_time.date()
        if cur is None or day!=cur:
            if cur is not None: daily.append(dayp)
            cur=day; dayp=0.; daily_loss=0.; cons=0; nday=0; stopped=False
        if stopped: skipped+=1; continue
        if cons>=5 or (bal>0 and daily_loss/bal>=0.02) or nday>=4:
            skipped+=1; continue
        conf=int(r.confidence)
        if cons>=3: rp=0.0025
        elif cons>=1: rp=0.005
        elif conf>=4: rp=0.01
        else: rp=0.005
        risk=bal*rp
        rm=float(r.r_multiple)
        # count published label/sign inconsistencies for audit
        signwin=rm>0
        labelwin=str(r.outcome).lower()=='win'
        if signwin!=labelwin: anomalies+=1
        raw=rm*risk
        if raw>0 and dayp+raw>=TARGET:
            pp=TARGET-dayp
        else:
            pp=raw
        bal+=pp; dayp+=pp; taken+=1; nday+=1
        if pp<0:
            losses+=1; cons+=1; daily_loss+=abs(pp)
        else:
            wins+=1; cons=0
        if dayp>=TARGET-1e-9:
            bal-=WITHDRAW; wd+=WITHDRAW; targets+=1; stopped=True
        peak=max(peak,bal); maxdd=max(maxdd,(peak-bal)/peak if peak>0 else 0)
        if bal<=0: break
    if cur is not None: daily.append(dayp)
    arr=pd.Series(daily,dtype=float)
    return {'start':start,'end':end,'failed':bal<=0,'ending_balance':round(bal,3),'withdrawn':round(wd,3),'economic_total':round(bal+wd,3),'net_economic_profit':round(bal+wd-START,3),'target_days':targets,'trade_days':len(set(x.entry_time.dt.date)),'trades_available':len(x),'trades_taken':taken,'trades_skipped_after_limits_or_target':skipped,'wins_taken':wins,'losses_taken':losses,'win_rate_pct':round(100*wins/taken,3) if taken else 0,'max_drawdown_pct':round(100*maxdd,3),'worst_day_pnl':round(float(arr.min()),3) if len(arr) else 0,'published_outcome_vs_r_sign_anomalies':anomalies}

def main(outdir):
    out=Path(outdir); out.mkdir(parents=True,exist_ok=True); d=load()
    r25=replay(d,'2025-01-01','2025-12-31 23:59:59')
    r26=replay(d,'2026-01-01','2026-10-29 23:59:59')
    rcombo=replay(d,'2025-01-01','2026-10-29 23:59:59')
    rep={'source':'TanvirCCC/algo-trading published OOS trade log','important':'Accounting replay of published R-multiples, NOT an independent Exness raw-tick reproduction of signals','risk_rules':'repo risk_manager: 0.5% base, 1% confidence>=4 clean slate, 0.5% after 1 loss, 0.25% after 3 losses, block after 5; daily loss cap 2%; max 4 trades/day','user_accounting':'start $1000; cap day at +$20; withdraw $10 and stop','2025':r25,'2026_to_oct29':r26,'continuous_2025_to_oct29_2026':rcombo}
    (out/'external_oos_replay.json').write_text(json.dumps(rep,indent=2)); print(json.dumps(rep,indent=2))
if __name__=='__main__':
    import argparse; ap=argparse.ArgumentParser(); ap.add_argument('--outdir',required=True); a=ap.parse_args(); main(a.outdir)

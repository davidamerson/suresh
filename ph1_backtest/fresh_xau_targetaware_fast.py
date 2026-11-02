import argparse, json
from pathlib import Path
import pandas as pd
import fresh_xau_daytrader_research as base
import fresh_xau_daytrader_vwap15 as vw
import fresh_xau_targetaware_daytrader as ta


def main(outdir):
    out=Path(outdir); out.mkdir(parents=True,exist_ok=True); work=out/'work'; work.mkdir(exist_ok=True)
    x24=vw.to15(base.load_year(2024,work)); fam={}
    for ses in ['BOTH','NY']:
      for strict in [1,2]: fam[f'{ses}_S{strict}']=vw.gen(x24,ses,strict)
    a=pd.Timestamp('2024-01-01',tz='UTC'); b=pd.Timestamp('2024-08-31 23:59:59',tz='UTC'); c=pd.Timestamp('2024-09-01',tz='UTC'); d=pd.Timestamp('2024-12-31 23:59:59',tz='UTC')
    stage1=[]
    for f,s in fam.items():
      for rr in [1.5,1.75,2.0,2.25,2.5]:
       for scheme in ['TARGET','TARGET_ONLY','TARGET_DECAY']:
        for br in [5.,7.5,10.]:
         r1=ta.sim(x24,s,rr,scheme,br,20.,40.,3,a,b); r2=ta.sim(x24,s,rr,scheme,br,20.,40.,3,c,d); sc=ta.score(r1,r2)
         stage1.append({'family':f,'rr':rr,'scheme':scheme,'base_risk':br,'score':sc,'train_profit':r1['net_economic_profit'],'hold_profit':r2['net_economic_profit'],'train_target':r1['target_day_rate_pct'],'hold_target':r2['target_day_rate_pct'],'train_dd':r1['max_drawdown_pct'],'hold_dd':r2['max_drawdown_pct']})
    s1=pd.DataFrame(stage1).sort_values('score',ascending=False); s1.to_csv(out/'stage1.csv',index=False)
    top=s1.head(18)[['family','rr','scheme','base_risk']].drop_duplicates().to_dict('records')
    stage2=[]
    for q in top:
      s=fam[q['family']]
      for rc in [15.,20.,25.,30.]:
       for cap in [30.,40.,50.]:
        r1=ta.sim(x24,s,q['rr'],q['scheme'],q['base_risk'],rc,cap,3,a,b); r2=ta.sim(x24,s,q['rr'],q['scheme'],q['base_risk'],rc,cap,3,c,d); sc=ta.score(r1,r2)
        stage2.append({**q,'risk_cap':rc,'daily_cap':cap,'score':sc,'train_profit':r1['net_economic_profit'],'hold_profit':r2['net_economic_profit'],'train_target':r1['target_day_rate_pct'],'hold_target':r2['target_day_rate_pct'],'train_dd':r1['max_drawdown_pct'],'hold_dd':r2['max_drawdown_pct']})
    sw=pd.DataFrame(stage2).sort_values('score',ascending=False); sw.to_csv(out/'stage2.csv',index=False); q=sw.iloc[0].to_dict(); win={k:q[k] for k in ['family','rr','scheme','base_risk','risk_cap','daily_cap']}; print('FROZEN',win,flush=True)
    r24=ta.sim(x24,fam[win['family']],win['rr'],win['scheme'],win['base_risk'],win['risk_cap'],win['daily_cap'],3,a,d); del x24,fam
    x25=vw.to15(base.load_year(2025,work)); s25=vw.gen(x25,win['family'].split('_')[0],int(win['family'][-1])); r25=ta.sim(x25,s25,win['rr'],win['scheme'],win['base_risk'],win['risk_cap'],win['daily_cap'],3,pd.Timestamp('2025-01-01',tz='UTC'),pd.Timestamp('2025-12-31 23:59:59',tz='UTC')); del x25,s25
    x26=vw.to15(base.load_year(2026,work)); s26=vw.gen(x26,win['family'].split('_')[0],int(win['family'][-1])); r26=ta.sim(x26,s26,win['rr'],win['scheme'],win['base_risk'],win['risk_cap'],win['daily_cap'],3,pd.Timestamp('2026-01-01',tz='UTC'),pd.Timestamp('2026-10-29 23:59:59',tz='UTC'))
    rep={'system':'Staged Target-Aware VWAP-EMA15 Day Trader','protocol':'2024 Jan-Aug screen + Sep-Dec holdout only; frozen before 2025/2026','winner':win,'accounting':{'start':1000,'daily_target':20,'withdraw':10},'2024':r24,'2025_validation':r25,'2026_validation':r26,'note':'capped target-aware risk, max 3 trades/day, no grid/martingale averaging, same-day flat'}
    (out/'final_report.json').write_text(json.dumps(rep,indent=2)); print(json.dumps(rep,indent=2),flush=True)
if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--outdir',required=True); a=ap.parse_args(); main(a.outdir)

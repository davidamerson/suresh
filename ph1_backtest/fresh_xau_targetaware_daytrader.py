import argparse, json, math
from pathlib import Path
import numpy as np
import pandas as pd
import fresh_xau_daytrader_research as base
import fresh_xau_daytrader_vwap15 as vw

START=1000.0; TARGET=20.0; WITHDRAW=10.0; COMM=7.0; LEV=2000.0; STEP=0.01; MAXLOT=0.30
DAYNS=86_400_000_000_000; MINNS=60_000_000_000

def pnl(d,e,x,l): return (x-e)*100.0*l*d-COMM*l

def sim(x,sigs,rr,scheme,base_risk,risk_cap,daily_cap,max_trades,start,end):
    d=x[(x.index>=start)&(x.index<=end)]
    sig=sigs[(sigs.time>=start)&(sigs.time<=end)].copy() if len(sigs) else sigs.copy()
    smap={}
    for r in sig.to_dict('records'):
        q=dict(r); q['endns']=int(pd.Timestamp(r['session_end']).value); smap.setdefault(int(pd.Timestamp(r['time']).value),[]).append(q)
    idx=d.index.view('int64'); dayk=idx//DAYNS
    bo=d.bid_o.to_numpy(float); bh=d.bid_h.to_numpy(float); bl=d.bid_l.to_numpy(float); bc=d.bid_c.to_numpy(float)
    ao=d.ask_o.to_numpy(float); ah=d.ask_h.to_numpy(float); al=d.ask_l.to_numpy(float); ac=d.ask_c.to_numpy(float); sp=d.spread_mean.to_numpy(float); ema=d.ema50.to_numpy(float)
    bal=START; wd=0.; trade=None; cur=-1; dayp=0.; nday=0; stopped=False; targetdays=0; traded=set(); trades=wins=losses=0; daily=[]; peak=START; maxdd=0.; failed=False; fdate=''; maxrisk=0.; maxlot=0.; consec=0
    for i in range(len(idx)):
        t=int(idx[i]); dk=int(dayk[i])
        if dk!=cur:
            if cur>=0: daily.append(dayp)
            cur=dk; dayp=0.; nday=0; stopped=False; consec=0
        if trade is not None:
            di,en,st,tp,lots,ens,endns=trade; ex=None
            if di>0:
                if bl[i]<=st: ex=st
                elif bh[i]>=tp: ex=tp
            else:
                if ah[i]>=st: ex=st
                elif al[i]<=tp: ex=tp
            if ex is None and (t>=endns or (t-ens)/MINNS>=360): ex=bc[i] if di>0 else ac[i]
            if ex is not None:
                pp=pnl(di,en,ex,lots); bal+=pp; dayp+=pp; trades+=1; traded.add(dk); wins+=pp>0; losses+=pp<=0; consec=0 if pp>0 else consec+1; trade=None
                if dayp>=TARGET-0.05:
                    bal-=WITHDRAW; wd+=WITHDRAW; targetdays+=1; stopped=True
                elif dayp<=-daily_cap: stopped=True
        eq=bal
        if trade is not None: eq+=pnl(trade[0],trade[1],bc[i] if trade[0]>0 else ac[i],trade[4])
        peak=max(peak,eq); maxdd=max(maxdd,(peak-eq)/peak if peak>0 else 0)
        if eq<=0 or bal<=0: failed=True; fdate=str(pd.Timestamp(t,unit='ns',tz='UTC').date()); break
        if trade is None and not stopped and nday<max_trades and t in smap:
            r=max(smap[t],key=lambda z:z['strength']); atr=float(r['atr']); di=int(r['direction'])
            if not np.isfinite(atr) or atr<=0 or sp[i]>0.8 or sp[i]>0.16*atr: continue
            en=ao[i] if di>0 else bo[i]; st=min(float(r['anchor']),en-0.9*atr) if di>0 else max(float(r['anchor']),en+0.9*atr); dist=abs(en-st)
            if dist<=0 or dist>2.2*atr: continue
            remaining=max(0.0,TARGET-dayp)
            if scheme=='FIXED': desired=base_risk
            elif scheme=='TARGET': desired=max(base_risk,remaining/rr)
            elif scheme=='TARGET_ONLY': desired=remaining/rr
            elif scheme=='TARGET_DECAY': desired=max(base_risk,remaining/rr)*(0.85**consec)
            else: desired=base_risk
            desired=min(risk_cap,desired)
            raw=desired/(dist*100.0+COMM); lots=math.floor((raw+1e-12)/STEP)*STEP; lots=min(MAXLOT,round(lots,2))
            if lots<STEP: continue
            actual=dist*100*lots+COMM*lots
            if actual>risk_cap*1.05: continue
            # Exact TP to finish the day at +$20, provided required R is not excessive.
            gross_needed=remaining+COMM*lots
            move=gross_needed/(100.0*lots)
            required_R=move/dist
            if required_R>rr*1.05: continue
            tp=en+move if di>0 else en-move
            mid=(bo[i]+ao[i])/2; margin=lots*100*mid/LEV
            if eq<=margin*1.25: continue
            trade=(di,en,st,tp,lots,t,int(r['endns'])); nday+=1; maxrisk=max(maxrisk,actual); maxlot=max(maxlot,lots)
    if cur>=0: daily.append(dayp)
    if trade is not None and len(idx):
        i=len(idx)-1; pp=pnl(trade[0],trade[1],bc[i] if trade[0]>0 else ac[i],trade[4]); bal+=pp; trades+=1; wins+=pp>0; losses+=pp<=0
    arr=np.array(daily,float); gp=arr[arr>0].sum() if len(arr) else 0.; gl=-arr[arr<0].sum() if len(arr) else 0.; pf=gp/gl if gl>1e-9 else (999 if gp>0 else 0); md=int(np.unique(dayk).size)
    return {'failed':failed,'failure_date':fdate,'ending_balance':round(bal,3),'withdrawn':round(wd,3),'economic_total':round(bal+wd,3),'net_economic_profit':round(bal+wd-START,3),'market_days':md,'target_days':targetdays,'target_day_rate_pct':round(100*targetdays/md,3),'traded_days':len(traded),'trades':trades,'wins':int(wins),'losses':int(losses),'win_rate_pct':round(100*wins/trades,3) if trades else 0,'profit_factor_day':round(pf,3),'max_drawdown_pct':round(100*maxdd,3),'worst_day_pnl':round(float(arr.min()),3) if len(arr) else 0,'max_trade_risk':round(maxrisk,3),'max_lot':maxlot}

def score(a,b):
    if a['failed'] or b['failed']: return -1e9
    # Aggressive but reject negative holdout or >35% DD in development/holdout.
    if a['net_economic_profit']<=0 or b['net_economic_profit']<=0: return -1e6+a['net_economic_profit']+b['net_economic_profit']
    dd=max(a['max_drawdown_pct'],b['max_drawdown_pct'])
    return 12*min(a['target_day_rate_pct'],b['target_day_rate_pct'])+20*min(a['profit_factor_day'],b['profit_factor_day'],2)+0.06*(a['net_economic_profit']+b['net_economic_profit'])-2.2*dd

def main(outdir):
    out=Path(outdir); out.mkdir(parents=True,exist_ok=True); work=out/'work'; work.mkdir(exist_ok=True)
    x24=vw.to15(base.load_year(2024,work)); fam={}
    for ses in ['BOTH','NY']:
      for strict in [1,2]: fam[f'{ses}_S{strict}']=vw.gen(x24,ses,strict)
    a=pd.Timestamp('2024-01-01',tz='UTC'); b=pd.Timestamp('2024-08-31 23:59:59',tz='UTC'); c=pd.Timestamp('2024-09-01',tz='UTC'); d=pd.Timestamp('2024-12-31 23:59:59',tz='UTC')
    rows=[]
    for f,s in fam.items():
      for rr in [1.5,1.75,2.0,2.25,2.5]:
       for scheme in ['TARGET','TARGET_ONLY','TARGET_DECAY']:
        for br in [5.,7.5,10.]:
         for rc in [15.,20.,25.,30.]:
          for cap in [30.,40.,50.]:
           r1=sim(x24,s,rr,scheme,br,rc,cap,3,a,b); r2=sim(x24,s,rr,scheme,br,rc,cap,3,c,d); sc=score(r1,r2)
           rows.append({'family':f,'rr':rr,'scheme':scheme,'base_risk':br,'risk_cap':rc,'daily_cap':cap,'score':sc,'train_profit':r1['net_economic_profit'],'hold_profit':r2['net_economic_profit'],'train_target':r1['target_day_rate_pct'],'hold_target':r2['target_day_rate_pct'],'train_dd':r1['max_drawdown_pct'],'hold_dd':r2['max_drawdown_pct']})
    sw=pd.DataFrame(rows).sort_values('score',ascending=False); sw.to_csv(out/'development_sweep.csv',index=False); q=sw.iloc[0].to_dict(); win={k:q[k] for k in ['family','rr','scheme','base_risk','risk_cap','daily_cap']}; print('FROZEN',win,flush=True)
    r24=sim(x24,fam[win['family']],win['rr'],win['scheme'],win['base_risk'],win['risk_cap'],win['daily_cap'],3,a,d); del x24,fam
    x25=vw.to15(base.load_year(2025,work)); s25=vw.gen(x25,win['family'].split('_')[0],int(win['family'][-1])); r25=sim(x25,s25,win['rr'],win['scheme'],win['base_risk'],win['risk_cap'],win['daily_cap'],3,pd.Timestamp('2025-01-01',tz='UTC'),pd.Timestamp('2025-12-31 23:59:59',tz='UTC')); del x25,s25
    x26=vw.to15(base.load_year(2026,work)); s26=vw.gen(x26,win['family'].split('_')[0],int(win['family'][-1])); r26=sim(x26,s26,win['rr'],win['scheme'],win['base_risk'],win['risk_cap'],win['daily_cap'],3,pd.Timestamp('2026-01-01',tz='UTC'),pd.Timestamp('2026-10-29 23:59:59',tz='UTC'))
    rep={'system':'Target-Aware VWAP-EMA15 Day Trader','protocol':'2024 Jan-Aug develop + Sep-Dec holdout; frozen before 2025/2026','winner':win,'accounting':{'start':1000,'daily_target':20,'withdraw':10},'2024':r24,'2025_validation':r25,'2026_validation':r26,'note':'Target-aware capped risk after losses; no grid, no averaging, max 3 trades/day'}
    (out/'final_report.json').write_text(json.dumps(rep,indent=2)); sw.head(100).to_csv(out/'top100.csv',index=False); print(json.dumps(rep,indent=2),flush=True)
if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--outdir',required=True); a=ap.parse_args(); main(a.outdir)

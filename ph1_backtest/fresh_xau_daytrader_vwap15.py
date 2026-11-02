import argparse, json, math
from pathlib import Path
import numpy as np
import pandas as pd
import fresh_xau_daytrader_research as base

START=1000.0; TARGET=20.0; WITHDRAW=10.0; COMM=7.0; LEV=2000.0; STEP=0.01; MAXLOT=0.25
DAYNS=86_400_000_000_000; MINNS=60_000_000_000

def to15(m5):
    a={'bid_o':'first','bid_h':'max','bid_l':'min','bid_c':'last','ask_o':'first','ask_h':'max','ask_l':'min','ask_c':'last','mid_o':'first','mid_h':'max','mid_l':'min','mid_c':'last','ticks':'sum','spread_mean':'mean'}
    x=m5.resample('15min',label='left',closed='left').agg(a).dropna(subset=['mid_o','mid_c'])
    c=x.mid_c; h=x.mid_h; l=x.mid_l; pc=c.shift(1)
    tr=pd.concat([(h-l),(h-pc).abs(),(l-pc).abs()],axis=1).max(axis=1)
    x['atr']=tr.ewm(alpha=1/14,adjust=False,min_periods=14).mean(); x['ema50']=c.ewm(span=50,adjust=False,min_periods=50).mean(); x['ema200']=c.ewm(span=200,adjust=False,min_periods=200).mean()
    typical=(h+l+c)/3; day=x.index.normalize(); x['vwap']=(typical*x.ticks).groupby(day).cumsum()/x.ticks.groupby(day).cumsum()
    rng=(h-l).replace(0,np.nan); x['body']=(c-x.mid_o).abs()/rng
    x['ema_slope']=(x.ema50-x.ema50.shift(4))/x.atr
    return x

def gen(x,session='BOTH',strict=1):
    rows=[]; prev=None; last=None
    for ts,r in x.iterrows():
        hm=ts.hour*60+ts.minute
        ok=(7*60<=hm<18*60) if session=='BOTH' else (12*60<=hm<18*60)
        if not ok or prev is None:
            prev=r; continue
        if not all(math.isfinite(float(r[k])) for k in ['atr','ema50','ema200','vwap','body','ema_slope']): prev=r; continue
        if last is not None and ts-last<pd.Timedelta(minutes=30): prev=r; continue
        atr=float(r.atr); shock=(r.mid_h-r.mid_l)>2.0*atr
        if shock: prev=r; continue
        longreg=r.ema50>r.ema200 and r.mid_c>r.vwap and r.ema_slope>0.03
        shortreg=r.ema50<r.ema200 and r.mid_c<r.vwap and r.ema_slope<-0.03
        if strict==2:
            longreg=longreg and (r.mid_c-r.ema200)<4.0*atr
            shortreg=shortreg and (r.ema200-r.mid_c)<4.0*atr
        if longreg:
            touched=min(prev.mid_l,r.mid_l)<=r.ema50+0.20*atr
            reject=r.mid_c>r.ema50 and r.mid_c>r.vwap and r.mid_c>r.mid_o and r.body>=0.35
            confirm=(strict==1 or r.mid_c>prev.mid_h)
            if touched and reject and confirm:
                anchor=min(prev.mid_l,r.mid_l)-0.10*atr; rows.append({'time':ts+pd.Timedelta(minutes=15),'direction':1,'atr':atr,'anchor':anchor,'session_end':ts.normalize()+pd.Timedelta(hours=20),'strength':r.body+max(r.ema_slope,0),'source':'VWAP_EMA15'}); last=ts
        elif shortreg:
            touched=max(prev.mid_h,r.mid_h)>=r.ema50-0.20*atr
            reject=r.mid_c<r.ema50 and r.mid_c<r.vwap and r.mid_c<r.mid_o and r.body>=0.35
            confirm=(strict==1 or r.mid_c<prev.mid_l)
            if touched and reject and confirm:
                anchor=max(prev.mid_h,r.mid_h)+0.10*atr; rows.append({'time':ts+pd.Timedelta(minutes=15),'direction':-1,'atr':atr,'anchor':anchor,'session_end':ts.normalize()+pd.Timedelta(hours=20),'strength':r.body+max(-r.ema_slope,0),'source':'VWAP_EMA15'}); last=ts
        prev=r
    return pd.DataFrame(rows)

def pnl(d,e,x,l): return (x-e)*100*l*d-COMM*l

def sim(x,sigs,risk,cap,mt,exit_mode,start,end):
    d=x[(x.index>=start)&(x.index<=end)]; sig=sigs[(sigs.time>=start)&(sigs.time<=end)] if len(sigs) else sigs
    smap={}
    for r in sig.to_dict('records'):
        q=dict(r); q['endns']=int(pd.Timestamp(r['session_end']).value); smap.setdefault(int(pd.Timestamp(r['time']).value),[]).append(q)
    idx=d.index.view('int64'); dk=idx//DAYNS
    bo=d.bid_o.to_numpy(float); bh=d.bid_h.to_numpy(float); bl=d.bid_l.to_numpy(float); bc=d.bid_c.to_numpy(float); ao=d.ask_o.to_numpy(float); ah=d.ask_h.to_numpy(float); al=d.ask_l.to_numpy(float); ac=d.ask_c.to_numpy(float); sp=d.spread_mean.to_numpy(float); ema=d.ema50.to_numpy(float)
    bal=START; wd=0.; tr=None; cur=-1; dayp=0.; nday=0; stopday=False; targets=0; traded=set(); trades=wins=losses=0; daily=[]; peak=START; maxdd=0.; failed=False; fdate=''; maxlot=0
    for i in range(len(idx)):
        t=int(idx[i]); day=int(dk[i])
        if day!=cur:
            if cur>=0: daily.append(dayp)
            cur=day; dayp=0.; nday=0; stopday=False
        if tr is not None:
            di,en,st,lots,ens,endns,armed=tr; ex=None
            # Initial structural stop is intrabar. Dynamic EMA exit is close-only.
            if di>0 and bl[i]<=st: ex=st
            elif di<0 and ah[i]>=st: ex=st
            else:
                exact=(TARGET-dayp+COMM*lots)/(100*lots)
                tgt=en+exact if di>0 else en-exact
                if dayp<TARGET and ((di>0 and bh[i]>=tgt) or (di<0 and al[i]<=tgt)): ex=tgt
                else:
                    favorable=(bh[i]-en if di>0 else en-al[i]); riskdist=abs(en-st)
                    if favorable>=riskdist: armed=True
                    if exit_mode=='EMA_ALWAYS' and ((di>0 and bc[i]<ema[i]) or (di<0 and ac[i]>ema[i])): ex=bc[i] if di>0 else ac[i]
                    elif exit_mode=='EMA_AFTER_1R' and armed and ((di>0 and bc[i]<ema[i]) or (di<0 and ac[i]>ema[i])): ex=bc[i] if di>0 else ac[i]
                    elif exit_mode=='HYBRID_2R':
                        tp=en+2*riskdist if di>0 else en-2*riskdist
                        if (di>0 and bh[i]>=tp) or (di<0 and al[i]<=tp): ex=tp
                        elif armed and ((di>0 and bc[i]<ema[i]) or (di<0 and ac[i]>ema[i])): ex=bc[i] if di>0 else ac[i]
                    if ex is None and (t>=endns or (t-ens)/MINNS>=360): ex=bc[i] if di>0 else ac[i]
            if ex is not None:
                pp=pnl(di,en,ex,lots); bal+=pp; dayp+=pp; trades+=1; traded.add(day); wins+=pp>0; losses+=pp<=0; tr=None
                if dayp>=TARGET-1e-8: bal-=WITHDRAW; wd+=WITHDRAW; targets+=1; stopday=True
                elif dayp<=-cap: stopday=True
            elif tr is not None: tr=(di,en,st,lots,ens,endns,armed)
        eq=bal
        if tr is not None: eq+=pnl(tr[0],tr[1],bc[i] if tr[0]>0 else ac[i],tr[3])
        peak=max(peak,eq); maxdd=max(maxdd,(peak-eq)/peak if peak>0 else 0)
        if eq<=0 or bal<=0: failed=True; fdate=str(pd.Timestamp(t,unit='ns',tz='UTC').date()); break
        if tr is None and not stopday and nday<mt and t in smap:
            r=max(smap[t],key=lambda z:z['strength']); atr=float(r['atr']); di=int(r['direction'])
            if atr<=0 or sp[i]>0.8 or sp[i]>0.16*atr: continue
            en=ao[i] if di>0 else bo[i]; st=min(float(r['anchor']),en-0.9*atr) if di>0 else max(float(r['anchor']),en+0.9*atr); dist=abs(en-st)
            if dist<=0 or dist>2.2*atr: continue
            raw=risk/(dist*100+COMM); lots=math.floor((raw+1e-12)/STEP)*STEP; lots=min(MAXLOT,round(lots,2))
            if lots<STEP: continue
            mid=(bo[i]+ao[i])/2; margin=lots*100*mid/LEV
            if eq<=margin*1.25: continue
            tr=(di,en,st,lots,t,int(r['endns']),False); nday+=1; maxlot=max(maxlot,lots)
    if cur>=0: daily.append(dayp)
    if tr is not None and len(idx):
        i=len(idx)-1; pp=pnl(tr[0],tr[1],bc[i] if tr[0]>0 else ac[i],tr[3]); bal+=pp; trades+=1; wins+=pp>0; losses+=pp<=0
    arr=np.array(daily,float); gp=arr[arr>0].sum() if len(arr) else 0; gl=-arr[arr<0].sum() if len(arr) else 0; pf=gp/gl if gl>1e-9 else (999 if gp>0 else 0); md=int(np.unique(dk).size)
    return {'failed':failed,'failure_date':fdate,'ending_balance':round(bal,3),'withdrawn':round(wd,3),'economic_total':round(bal+wd,3),'net_economic_profit':round(bal+wd-START,3),'market_days':md,'target_days':targets,'target_day_rate_pct':round(100*targets/md,3) if md else 0,'traded_days':len(traded),'trades':trades,'wins':int(wins),'losses':int(losses),'win_rate_pct':round(100*wins/trades,3) if trades else 0,'profit_factor_day':round(pf,3),'max_drawdown_pct':round(100*maxdd,3),'worst_day_pnl':round(float(arr.min()),3) if len(arr) else 0,'max_lot':maxlot}

def score(a,b):
    if a['failed'] or b['failed']: return -1e9
    if a['net_economic_profit']<=0 or b['net_economic_profit']<=0: return -1e6+a['net_economic_profit']+b['net_economic_profit']
    return 7*min(a['target_day_rate_pct'],b['target_day_rate_pct'])+18*min(a['profit_factor_day'],b['profit_factor_day'],2)-1.5*max(a['max_drawdown_pct'],b['max_drawdown_pct'])+0.05*(a['net_economic_profit']+b['net_economic_profit'])

def main(outdir):
    out=Path(outdir); out.mkdir(parents=True,exist_ok=True); work=out/'work'; work.mkdir(exist_ok=True)
    x24=to15(base.load_year(2024,work)); families={}
    for ses in ['BOTH','NY']:
        for strict in [1,2]: families[f'{ses}_S{strict}']=gen(x24,ses,strict)
    print('SIGNALS24',{k:len(v) for k,v in families.items()},flush=True)
    a=pd.Timestamp('2024-01-01',tz='UTC'); b=pd.Timestamp('2024-08-31 23:59:59',tz='UTC'); c=pd.Timestamp('2024-09-01',tz='UTC'); d=pd.Timestamp('2024-12-31 23:59:59',tz='UTC')
    rows=[]
    for fam,s in families.items():
      for risk in [10.,12.5,15.,17.5,20.]:
       for cap in [20.,30.,40.]:
        for mt in [2,3]:
         for mode in ['EMA_ALWAYS','EMA_AFTER_1R','HYBRID_2R']:
          r1=sim(x24,s,risk,cap,mt,mode,a,b); r2=sim(x24,s,risk,cap,mt,mode,c,d); rows.append({'family':fam,'risk':risk,'cap':cap,'mt':mt,'mode':mode,'score':score(r1,r2),'train_profit':r1['net_economic_profit'],'hold_profit':r2['net_economic_profit'],'train_target':r1['target_day_rate_pct'],'hold_target':r2['target_day_rate_pct'],'train_dd':r1['max_drawdown_pct'],'hold_dd':r2['max_drawdown_pct']})
    sw=pd.DataFrame(rows).sort_values('score',ascending=False); sw.to_csv(out/'development_sweep.csv',index=False); q=sw.iloc[0].to_dict(); win={k:q[k] for k in ['family','risk','cap','mt','mode']}; print('FROZEN',win,flush=True)
    r24=sim(x24,families[win['family']],win['risk'],win['cap'],int(win['mt']),win['mode'],a,d); del x24,families
    x25=to15(base.load_year(2025,work)); s25=gen(x25,win['family'].split('_')[0],int(win['family'][-1])); r25=sim(x25,s25,win['risk'],win['cap'],int(win['mt']),win['mode'],pd.Timestamp('2025-01-01',tz='UTC'),pd.Timestamp('2025-12-31 23:59:59',tz='UTC')); del x25,s25
    x26=to15(base.load_year(2026,work)); s26=gen(x26,win['family'].split('_')[0],int(win['family'][-1])); r26=sim(x26,s26,win['risk'],win['cap'],int(win['mt']),win['mode'],pd.Timestamp('2026-01-01',tz='UTC'),pd.Timestamp('2026-10-29 23:59:59',tz='UTC'))
    rep={'system':'VWAP-EMA15 Dynamic Day Trader','protocol':'2024 Jan-Aug develop + Sep-Dec holdout; frozen before 2025/2026','winner':win,'accounting':{'start':1000,'daily_target':20,'withdraw_on_target':10},'2024':r24,'2025_validation':r25,'2026_validation':r26,'execution':{'raw_spread_bid_ask':True,'commission_per_lot_rt':7,'same_bar_stop_first':True,'flat_same_day':True,'no_martingale':True}}
    (out/'final_report.json').write_text(json.dumps(rep,indent=2)); sw.head(50).to_csv(out/'top50.csv',index=False); print(json.dumps(rep,indent=2),flush=True)
if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--outdir',required=True); args=ap.parse_args(); main(args.outdir)

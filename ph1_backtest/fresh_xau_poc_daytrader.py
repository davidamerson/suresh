import argparse, json, math
from pathlib import Path
import numpy as np
import pandas as pd
import fresh_xau_daytrader_research as m


def build_profile(x, start_i, end_i, atr, bin_frac):
    if end_i <= start_i + 2 or not math.isfinite(atr) or atr <= 0:
        return None
    leg=x.iloc[start_i:end_i+1]
    p=((leg.mid_h+leg.mid_l+leg.mid_c)/3.0).to_numpy(float)
    w=leg.ticks.to_numpy(float)
    lo=float(np.nanmin(leg.mid_l)); hi=float(np.nanmax(leg.mid_h)); bw=max(bin_frac*atr,0.05)
    if hi-lo < 3*bw: return None
    edges=np.arange(lo,hi+bw*1.01,bw)
    if len(edges)<4: return None
    hist,_=np.histogram(p,bins=edges,weights=w)
    if hist.sum()<=0: return None
    centers=(edges[:-1]+edges[1:])/2
    poc_i=int(np.argmax(hist)); poc=float(centers[poc_i])
    order=np.argsort(hist)[::-1]; total=hist.sum(); s=0.; selected=[]
    for j in order:
        selected.append(int(j)); s+=hist[j]
        if s>=0.70*total: break
    val=float(edges[min(selected)]); vah=float(edges[max(selected)+1])
    return {'poc':poc,'val':val,'vah':vah,'lo':lo,'hi':hi}


def gen_poc(x,pivot_n=3,bin_frac=0.25,tol=0.25,bidir=False):
    rows=[]; last_low=None; last_high=None; profiles=[]; cooldown=None
    H=x.mid_h.to_numpy(float); L=x.mid_l.to_numpy(float); C=x.mid_c.to_numpy(float); O=x.mid_o.to_numpy(float); ATR=x.atr.to_numpy(float)
    idx=x.index
    for i in range(2*pivot_n,len(x)):
        ts=idx[i]; p=i-pivot_n
        # Causal pivots: pivot only known after N later bars.
        winH=H[p-pivot_n:p+pivot_n+1]; winL=L[p-pivot_n:p+pivot_n+1]
        if len(winH)==2*pivot_n+1:
            if H[p]>=np.nanmax(winH):
                last_high=p
                if last_low is not None and last_low<p:
                    atr=ATR[i]
                    if math.isfinite(atr) and H[p]-L[last_low]>=1.5*atr:
                        prof=build_profile(x,last_low,p,atr,bin_frac)
                        if prof:
                            prof.update({'dir':1,'created_i':i,'break':False,'expires':i+144,'used':False}); profiles.append(prof)
            if L[p]<=np.nanmin(winL):
                last_low=p
                if bidir and last_high is not None and last_high<p:
                    atr=ATR[i]
                    if math.isfinite(atr) and H[last_high]-L[p]>=1.5*atr:
                        prof=build_profile(x,last_high,p,atr,bin_frac)
                        if prof:
                            prof.update({'dir':-1,'created_i':i,'break':False,'expires':i+144,'used':False}); profiles.append(prof)

        atr=ATR[i]
        if not math.isfinite(atr) or atr<=0: continue
        hm=ts.hour*60+ts.minute
        entrytime=12*60<=hm<17*60+30
        if cooldown is not None and ts<cooldown: entrytime=False
        # Only retain recent causal profiles.
        profiles=[q for q in profiles if not q['used'] and i<=q['expires']]
        for q in profiles:
            d=q['dir']
            # Trend filter using completed H1 regime from parent engine.
            h1ok=True
            try:
                if d>0: h1ok=(x.h1_close.iloc[i]>x.h1_ema50.iloc[i]>x.h1_ema200.iloc[i])
                else: h1ok=(x.h1_close.iloc[i]<x.h1_ema50.iloc[i]<x.h1_ema200.iloc[i])
            except Exception: pass
            if not h1ok: continue
            if not q['break']:
                if d>0 and C[i]>q['vah']+0.08*atr: q['break']=True
                elif d<0 and C[i]<q['val']-0.08*atr: q['break']=True
                continue
            if not entrytime: continue
            rng=max(H[i]-L[i],1e-9); body=abs(C[i]-O[i])/rng
            if d>0:
                touched=L[i]<=q['poc']+tol*atr
                accepted=C[i]>q['poc'] and C[i]>O[i] and C[i]>x.tvwap.iloc[i] and body>=0.30
                if touched and accepted:
                    anchor=min(L[i]-0.10*atr,q['val']-0.10*atr)
                    rows.append(m.signal(ts,1,atr,anchor,body+0.8,'POC_RETEST_LONG')); q['used']=True; cooldown=ts+pd.Timedelta(minutes=30); break
                if C[i]<q['val']-0.40*atr: q['used']=True
            else:
                touched=H[i]>=q['poc']-tol*atr
                accepted=C[i]<q['poc'] and C[i]<O[i] and C[i]<x.tvwap.iloc[i] and body>=0.30
                if touched and accepted:
                    anchor=max(H[i]+0.10*atr,q['vah']+0.10*atr)
                    rows.append(m.signal(ts,-1,atr,anchor,body+0.8,'POC_RETEST_SHORT')); q['used']=True; cooldown=ts+pd.Timedelta(minutes=30); break
                if C[i]>q['vah']+0.40*atr: q['used']=True
    return pd.DataFrame(rows)


def score(a,b):
    if a['failed'] or b['failed']: return -1e9
    if a['net_economic_profit']<=0 or b['net_economic_profit']<=0: return -1e6+a['net_economic_profit']+b['net_economic_profit']
    return 8*min(a['target_day_rate_pct'],b['target_day_rate_pct'])+20*min(a['profit_factor_day'],b['profit_factor_day'],2)-1.8*max(a['max_drawdown_pct'],b['max_drawdown_pct'])+0.05*(a['net_economic_profit']+b['net_economic_profit'])


def main(outdir):
    out=Path(outdir); out.mkdir(parents=True,exist_ok=True); work=out/'work'; work.mkdir(exist_ok=True)
    print('POC-INSPIRED APPROXIMATION: public methodology, not proprietary implementation',flush=True)
    x24=m.add_indicators(m.load_year(2024,work))
    a=pd.Timestamp('2024-01-01',tz='UTC'); b=pd.Timestamp('2024-08-31 23:59:59',tz='UTC'); c=pd.Timestamp('2024-09-01',tz='UTC'); d=pd.Timestamp('2024-12-31 23:59:59',tz='UTC')
    configs=[]
    signal_cache={}
    for pn in [2,3,4]:
      for bf in [0.18,0.25,0.35]:
       for tol in [0.15,0.30]:
        for bd in [False,True]:
         key=(pn,bf,tol,bd); s=gen_poc(x24,pn,bf,tol,bd); signal_cache[key]=s; print('SIG',key,len(s),flush=True)
         for rr in [1.5,2.0,2.5]:
          for risk in [10.,15.,17.5]:
           tr=m.simulate(x24,s,rr,risk,30.,2,a,b); ho=m.simulate(x24,s,rr,risk,30.,2,c,d)
           configs.append({'pn':pn,'bin_frac':bf,'tol':tol,'bidir':bd,'rr':rr,'risk':risk,'score':score(tr,ho),'train_profit':tr['net_economic_profit'],'hold_profit':ho['net_economic_profit'],'train_target':tr['target_day_rate_pct'],'hold_target':ho['target_day_rate_pct'],'train_dd':tr['max_drawdown_pct'],'hold_dd':ho['max_drawdown_pct']})
    sw=pd.DataFrame(configs).sort_values('score',ascending=False); sw.to_csv(out/'development_sweep.csv',index=False); q=sw.iloc[0].to_dict(); win={k:q[k] for k in ['pn','bin_frac','tol','bidir','rr','risk']}; print('FROZEN',win,flush=True)
    key=(int(win['pn']),float(win['bin_frac']),float(win['tol']),bool(win['bidir'])); r24=m.simulate(x24,signal_cache[key],win['rr'],win['risk'],30.,2,a,d); del x24,signal_cache
    x25=m.add_indicators(m.load_year(2025,work)); s25=gen_poc(x25,*key); r25=m.simulate(x25,s25,win['rr'],win['risk'],30.,2,pd.Timestamp('2025-01-01',tz='UTC'),pd.Timestamp('2025-12-31 23:59:59',tz='UTC')); count25=len(s25); del x25,s25
    x26=m.add_indicators(m.load_year(2026,work)); s26=gen_poc(x26,*key); r26=m.simulate(x26,s26,win['rr'],win['risk'],30.,2,pd.Timestamp('2026-01-01',tz='UTC'),pd.Timestamp('2026-10-29 23:59:59',tz='UTC')); count26=len(s26)
    rep={'system':'POC-inspired Causal Swing Retest Day Trader','note':'Reproducible approximation of public POC methodology; NOT the proprietary author implementation','protocol':'2024 develop/holdout, frozen before 2025/2026','winner':win,'accounting':{'start':1000,'target':20,'withdraw':10},'2024':r24,'2025_validation':r25,'2026_validation':r26,'signals_2025':count25,'signals_2026':count26}
    (out/'final_report.json').write_text(json.dumps(rep,indent=2)); print(json.dumps(rep,indent=2),flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--outdir',required=True); args=ap.parse_args(); main(args.outdir)

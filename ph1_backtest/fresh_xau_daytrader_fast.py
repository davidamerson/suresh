import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
import fresh_xau_daytrader_research as m

DAY_NS=m.DAY_NS; MIN_NS=m.MIN_NS


def fast_simulate(x,signals,rr,risk_usd,daily_loss_cap,max_trades_day,start,end):
    d=x[(x.index>=start)&(x.index<=end)]
    if len(d)==0: return None
    sig=signals[(signals['time']>=start)&(signals['time']<=end)].copy() if len(signals) else signals.copy()
    smap={}
    if len(sig):
        for r in sig.to_dict('records'):
            key=int(pd.Timestamp(r['time']).value); rec=dict(r); rec['session_end_ns']=int(pd.Timestamp(r['session_end']).value)
            smap.setdefault(key,[]).append(rec)

    idx=d.index.view('int64'); daykey=idx//DAY_NS
    bo=d['bid_o'].to_numpy(float); bh=d['bid_h'].to_numpy(float); bl=d['bid_l'].to_numpy(float); bc=d['bid_c'].to_numpy(float)
    ao=d['ask_o'].to_numpy(float); ah=d['ask_h'].to_numpy(float); al=d['ask_l'].to_numpy(float); ac=d['ask_c'].to_numpy(float)
    sp=d['spread_mean'].to_numpy(float)
    balance=m.START_BALANCE; withdrawn=0.0; trade=None; curday=-1; dayreal=0.0; daytrades=0; stopped=False
    target_days=0; traded_days=set(); trades=0; wins=0; losses=0; daily=[]; peak=m.START_BALANCE; maxdd=0.0; failed=False; faildate=''
    max_lot=0.0; max_risk=0.0; source_counts={}

    for i in range(len(idx)):
        tns=int(idx[i]); dk=int(daykey[i])
        if dk!=curday:
            if curday>=0: daily.append(dayreal)
            curday=dk; dayreal=0.0; daytrades=0; stopped=False

        if trade is not None:
            direction=trade[0]; entry=trade[1]; stop=trade[2]; tp=trade[3]; lots=trade[4]; ens=trade[5]; send=trade[6]
            exit_px=None
            if direction>0:
                if bl[i]<=stop: exit_px=stop
                else:
                    exact=(m.DAILY_TARGET-dayreal+m.COMMISSION_PER_LOT_RT*lots)/(100.0*lots)+entry
                    if dayreal<m.DAILY_TARGET and bh[i]>=exact: exit_px=exact
                    elif bh[i]>=tp: exit_px=tp
            else:
                if ah[i]>=stop: exit_px=stop
                else:
                    exact=entry-(m.DAILY_TARGET-dayreal+m.COMMISSION_PER_LOT_RT*lots)/(100.0*lots)
                    if dayreal<m.DAILY_TARGET and al[i]<=exact: exit_px=exact
                    elif al[i]<=tp: exit_px=tp
            if exit_px is None and (tns>=send or (tns-ens)/MIN_NS>=m.MAX_HOLD_MIN):
                exit_px=bc[i] if direction>0 else ac[i]
            if exit_px is not None:
                pnl=m.trade_pnl(direction,entry,exit_px,lots); balance+=pnl; dayreal+=pnl; trades+=1; traded_days.add(dk)
                if pnl>0: wins+=1
                else: losses+=1
                trade=None
                if dayreal>=m.DAILY_TARGET-1e-8:
                    withdrawn+=m.DAILY_WITHDRAW; balance-=m.DAILY_WITHDRAW; target_days+=1; stopped=True
                elif dayreal<=-daily_loss_cap+1e-8: stopped=True

        equity=balance
        if trade is not None:
            px=bc[i] if trade[0]>0 else ac[i]
            equity+=m.trade_pnl(trade[0],trade[1],px,trade[4])
        if equity>peak: peak=equity
        if peak>0:
            dd=(peak-equity)/peak
            if dd>maxdd: maxdd=dd
        if equity<=0 or balance<=0:
            failed=True; faildate=str(pd.Timestamp(tns,unit='ns',tz='UTC').date()); break

        if trade is None and not stopped and daytrades<max_trades_day and tns in smap:
            opts=sorted(smap[tns],key=lambda r:r['strength'],reverse=True)
            for r in opts:
                atr=float(r['atr']); direction=int(r['direction'])
                if not np.isfinite(atr) or atr<=0 or sp[i]>m.SPREAD_HARD_CAP or sp[i]>0.16*atr: continue
                entry=ao[i] if direction>0 else bo[i]
                if direction>0: stop=min(float(r['anchor']),entry-0.85*atr); dist=entry-stop
                else: stop=max(float(r['anchor']),entry+0.85*atr); dist=stop-entry
                if dist<=0 or dist>2.20*atr: continue
                raw=risk_usd/(dist*100.0+m.COMMISSION_PER_LOT_RT)
                lots=np.floor((raw+1e-12)/m.LOT_STEP)*m.LOT_STEP; lots=min(m.MAX_LOT,round(float(lots),2))
                if lots<m.LOT_STEP: continue
                actual=dist*100.0*lots+m.COMMISSION_PER_LOT_RT*lots
                if actual>risk_usd*1.20: continue
                mid=0.5*(bo[i]+ao[i]); margin=lots*100.0*mid/m.LEVERAGE
                if equity<=margin*1.25: continue
                tp=entry+rr*dist if direction>0 else entry-rr*dist
                trade=(direction,entry,stop,tp,lots,tns,int(r['session_end_ns']))
                daytrades+=1; max_lot=max(max_lot,lots); max_risk=max(max_risk,actual); source_counts[r['source']]=source_counts.get(r['source'],0)+1
                break

    if curday>=0: daily.append(dayreal)
    if trade is not None and len(idx):
        i=len(idx)-1; px=bc[i] if trade[0]>0 else ac[i]; pnl=m.trade_pnl(trade[0],trade[1],px,trade[4]); balance+=pnl; dayreal+=pnl; trades+=1
        if pnl>0: wins+=1
        else: losses+=1
    arr=np.array(daily,float) if daily else np.array([]); gp=float(arr[arr>0].sum()) if len(arr) else 0.0; gl=float(-arr[arr<0].sum()) if len(arr) else 0.0
    pf=gp/gl if gl>1e-9 else (999.0 if gp>0 else 0.0); market_days=int(np.unique(daykey).size)
    return {'failed':failed,'failure_date':faildate,'ending_balance':round(balance,3),'withdrawn':round(withdrawn,3),'economic_total':round(balance+withdrawn,3),'net_economic_profit':round(balance+withdrawn-m.START_BALANCE,3),'market_days':market_days,'target_days':target_days,'target_day_rate_pct':round(100*target_days/market_days,3) if market_days else 0.0,'traded_days':len(traded_days),'trades':trades,'wins':wins,'losses':losses,'win_rate_pct':round(100*wins/trades,3) if trades else 0.0,'loss_days':int((arr<0).sum()) if len(arr) else 0,'profit_factor_day':round(pf,3),'max_drawdown_pct':round(100*maxdd,3),'worst_day_pnl':round(float(arr.min()),3) if len(arr) else 0.0,'max_lot':round(max_lot,3),'max_planned_trade_risk':round(max_risk,3),'source_entries':source_counts}

m.simulate=fast_simulate


def main(outdir):
    out=Path(outdir); out.mkdir(parents=True,exist_ok=True); work=out/'work'; work.mkdir(exist_ok=True)
    print('=== 2024 DEVELOPMENT ===',flush=True)
    x24=m.add_indicators(m.load_year(2024,work)); f24=m.make_families(x24); print('SIGNALS 2024',{k:len(v) for k,v in f24.items()},flush=True)
    a=pd.Timestamp('2024-01-01',tz='UTC'); b=pd.Timestamp('2024-08-31 23:59:59',tz='UTC'); c=pd.Timestamp('2024-09-01',tz='UTC'); d=pd.Timestamp('2024-12-31 23:59:59',tz='UTC')
    stage1=[]
    for family,sigs in f24.items():
        for rr in [1.5,1.75,2.0,2.25,2.5]:
            for risk in [10.0,12.5,15.0,17.5]:
                tr=fast_simulate(x24,sigs,rr,risk,30.0,2,a,b); ho=fast_simulate(x24,sigs,rr,risk,30.0,2,c,d); sc=m.score_pair(tr,ho)
                stage1.append({'family':family,'rr':rr,'risk_usd':risk,'score':sc,'train_target_rate':tr['target_day_rate_pct'],'train_profit':tr['net_economic_profit'],'hold_target_rate':ho['target_day_rate_pct'],'hold_profit':ho['net_economic_profit']})
    s1=pd.DataFrame(stage1).sort_values('score',ascending=False); s1.to_csv(out/'stage1_entry_risk_screen.csv',index=False)
    top=s1.head(12)[['family','rr','risk_usd']].drop_duplicates().to_dict('records')
    stage2=[]
    for q in top:
        sigs=f24[q['family']]
        for cap in [20.0,25.0,30.0,35.0]:
            for mt in [2,3]:
                tr=fast_simulate(x24,sigs,q['rr'],q['risk_usd'],cap,mt,a,b); ho=fast_simulate(x24,sigs,q['rr'],q['risk_usd'],cap,mt,c,d); sc=m.score_pair(tr,ho)
                stage2.append({**q,'daily_loss_cap':cap,'max_trades_day':mt,'score':sc,'train_target_rate':tr['target_day_rate_pct'],'train_profit':tr['net_economic_profit'],'train_pf':tr['profit_factor_day'],'train_dd':tr['max_drawdown_pct'],'hold_target_rate':ho['target_day_rate_pct'],'hold_profit':ho['net_economic_profit'],'hold_pf':ho['profit_factor_day'],'hold_dd':ho['max_drawdown_pct']})
    sweep=pd.DataFrame(stage2).sort_values('score',ascending=False); sweep.to_csv(out/'stage2_risk_refinement.csv',index=False)
    best=sweep.iloc[0].to_dict(); winner={k:best[k] for k in ['family','rr','risk_usd','daily_loss_cap','max_trades_day']}; print('FROZEN WINNER',winner,flush=True)
    r24=fast_simulate(x24,f24[winner['family']],winner['rr'],winner['risk_usd'],winner['daily_loss_cap'],int(winner['max_trades_day']),pd.Timestamp('2024-01-01',tz='UTC'),d); del x24,f24

    print('=== UNTOUCHED 2025 ===',flush=True)
    x25=m.add_indicators(m.load_year(2025,work)); f25=m.make_families(x25); r25=fast_simulate(x25,f25[winner['family']],winner['rr'],winner['risk_usd'],winner['daily_loss_cap'],int(winner['max_trades_day']),pd.Timestamp('2025-01-01',tz='UTC'),pd.Timestamp('2025-12-31 23:59:59',tz='UTC')); counts25={k:len(v) for k,v in f25.items()}; del x25,f25
    print('=== UNTOUCHED 2026 ===',flush=True)
    x26=m.add_indicators(m.load_year(2026,work)); f26=m.make_families(x26); r26=fast_simulate(x26,f26[winner['family']],winner['rr'],winner['risk_usd'],winner['daily_loss_cap'],int(winner['max_trades_day']),pd.Timestamp('2026-01-01',tz='UTC'),pd.Timestamp('2026-10-29 23:59:59',tz='UTC')); counts26={k:len(v) for k,v in f26.items()}
    report={'system_name':'NY Structural-Retest Day Trader','development_protocol':'2024 Jan-Aug screen + Sep-Dec holdout; frozen before 2025/2026','winner':winner,'accounting':{'start_balance':1000,'daily_target':20,'withdraw_on_target':10},'2024_development':r24,'2025_validation':r25,'2026_validation_to_oct29':r26,'signal_counts_2025':counts25,'signal_counts_2026':counts26,'execution':{'data':'Exness XAUUSD Raw Spread ticks -> 5m bid/ask bars','commission_per_lot_round_trip':7.0,'leverage':2000,'same_bar_stop_vs_target':'stop first','max_hold_minutes':m.MAX_HOLD_MIN,'no_martingale':True,'no_overnight':True}}
    (out/'final_report.json').write_text(json.dumps(report,indent=2)); pd.DataFrame([{'period':'2024 development',**r24},{'period':'2025 validation',**r25},{'period':'2026 validation',**r26}]).to_csv(out/'period_results.csv',index=False); print(json.dumps(report,indent=2),flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--outdir',required=True); args=ap.parse_args(); main(args.outdir)

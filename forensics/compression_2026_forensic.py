import math, zipfile
from pathlib import Path
import numpy as np
import pandas as pd
from numba import njit

# Reuse the exact signal construction and downloader from the tested Entry10 engine.
from ph1_backtest.entry10_adaptive_sweep import download, aggregate_zip_to_minutes, build_signals

START_BALANCE=1000.0
TARGET=10.0
COMMISSION=0.07
LEVERAGE=2000.0
BASE_STEP=1.0

@njit(cache=True)
def gap_from_switches(sw):
    n=sw+1
    return BASE_STEP*n*(n+1)/2.0

@njit(cache=True)
def replay(ts,bids,asks,sig_t,sig_d,sig_n,
           st_i,st_f,
           ledger_day,ledger_pnl,ledger_target,ledger_maxpos,ledger_balance,ledger_withdrawn,ledger_n,
           ev_t,ev_side,ev_fill,ev_pos,ev_sw,ev_liq,ev_gap,ev_n,
           fail_i,fail_f):
    # st_i: initialized,last_day,sig_ptr,open_n,buy_n,sell_n,last_side,switches,stopped,day_activity,day_target,day_maxpos,failed
    # st_f: balance,withdrawn,buy_sum,sell_sum,up_outer,dn_outer,next_up,next_dn,day_realized,last_bid,last_ask,min_eq
    initialized=st_i[0]; last_day=st_i[1]; sig_ptr=st_i[2]
    open_n=st_i[3]; buy_n=st_i[4]; sell_n=st_i[5]; last_side=st_i[6]; switches=st_i[7]
    stopped=st_i[8]; day_activity=st_i[9]; day_target=st_i[10]; day_maxpos=st_i[11]; failed=st_i[12]
    balance=st_f[0]; withdrawn=st_f[1]; buy_sum=st_f[2]; sell_sum=st_f[3]
    up_outer=st_f[4]; dn_outer=st_f[5]; next_up=st_f[6]; next_dn=st_f[7]; day_realized=st_f[8]
    last_bid=st_f[9]; last_ask=st_f[10]; min_eq=st_f[11]
    ln=ledger_n[0]; en=ev_n[0]

    for j in range(len(ts)):
        t=ts[j]; bid=bids[j]; ask=asks[j]
        if not (math.isfinite(bid) and math.isfinite(ask)): continue
        day=t//86400000000000; dow=(day+3)%7
        if initialized==0:
            initialized=1; last_day=day; last_bid=bid; last_ask=ask

        if day!=last_day:
            prev_dow=(last_day+3)%7
            if prev_dow==4 and failed==0 and open_n>0:
                liq=buy_n*last_bid-buy_sum+sell_sum-sell_n*last_ask-open_n*COMMISSION
                balance+=liq; day_realized+=liq
                open_n=0;buy_n=0;sell_n=0;buy_sum=0.0;sell_sum=0.0;last_side=0;switches=0
            if day_activity!=0 and ln<len(ledger_day):
                ledger_day[ln]=last_day; ledger_pnl[ln]=day_realized; ledger_target[ln]=day_target
                ledger_maxpos[ln]=day_maxpos; ledger_balance[ln]=balance; ledger_withdrawn[ln]=withdrawn; ln+=1
            day_realized=0.0;day_activity=0;day_target=0;day_maxpos=0;stopped=0
            last_day=day

        if failed!=0:
            last_bid=bid; last_ask=ask
            continue

        if open_n>0:
            day_activity=1
            if open_n>day_maxpos: day_maxpos=open_n
            liq=buy_n*bid-buy_sum+sell_sum-sell_n*ask-open_n*COMMISSION
            if day_realized+liq>=TARGET:
                balance+=liq; day_realized+=liq
                open_n=0;buy_n=0;sell_n=0;buy_sum=0.0;sell_sum=0.0;last_side=0;switches=0
                day_target=1;stopped=1;balance-=TARGET;withdrawn+=TARGET

        while sig_ptr<sig_n and sig_t[sig_ptr]<=t:
            d=sig_d[sig_ptr]; sig_ptr+=1
            if open_n!=0 or stopped!=0: continue
            if dow>=4: continue
            fill=ask if d>0 else bid
            req=fill/LEVERAGE
            if balance<req:
                failed=1; fail_i[0]=1; fail_i[1]=day; fail_i[2]=t
                fail_i[3]=open_n; fail_i[4]=buy_n; fail_i[5]=sell_n; fail_i[6]=switches
                fail_f[0]=balance; fail_f[1]=balance; fail_f[2]=bid; fail_f[3]=ask; fail_f[4]=0.0
                break
            open_n=1
            if d>0:
                buy_n=1;buy_sum=fill;sell_n=0;sell_sum=0.0;last_side=1
            else:
                sell_n=1;sell_sum=fill;buy_n=0;buy_sum=0.0;last_side=-1
            switches=0;up_outer=fill;dn_outer=fill
            g=gap_from_switches(0);next_up=fill+g;next_dn=fill-g;day_activity=1
            if en<len(ev_t):
                ev_t[en]=t;ev_side[en]=d;ev_fill[en]=fill;ev_pos[en]=open_n;ev_sw[en]=switches;ev_liq[en]=0.0;ev_gap[en]=g;en+=1
            break

        if open_n>0 and failed==0:
            for _ in range(12):
                acted=0
                if bid>=next_up:
                    liq=buy_n*bid-buy_sum+sell_sum-sell_n*ask-open_n*COMMISSION
                    if liq>0.0:
                        balance+=liq;day_realized+=liq;open_n=0;buy_n=0;sell_n=0;buy_sum=0.0;sell_sum=0.0;last_side=0;switches=0
                    else:
                        fill=ask;eq=balance+liq;margin=open_n*((bid+ask)*0.5)/LEVERAGE;req=fill/LEVERAGE
                        if eq-margin<req:
                            failed=1; fail_i[0]=2; fail_i[1]=day; fail_i[2]=t; fail_i[3]=open_n; fail_i[4]=buy_n; fail_i[5]=sell_n; fail_i[6]=switches
                            fail_f[0]=balance; fail_f[1]=eq; fail_f[2]=bid; fail_f[3]=ask; fail_f[4]=liq
                        else:
                            if last_side==-1:switches+=1
                            last_side=1;buy_n+=1;buy_sum+=fill;open_n+=1;up_outer=next_up;g=gap_from_switches(switches);next_up=up_outer+g;next_dn=dn_outer-g
                            if en<len(ev_t):
                                ev_t[en]=t;ev_side[en]=1;ev_fill[en]=fill;ev_pos[en]=open_n;ev_sw[en]=switches;ev_liq[en]=liq;ev_gap[en]=g;en+=1
                    acted=1
                elif bid<=next_dn:
                    liq=buy_n*bid-buy_sum+sell_sum-sell_n*ask-open_n*COMMISSION
                    if liq>0.0:
                        balance+=liq;day_realized+=liq;open_n=0;buy_n=0;sell_n=0;buy_sum=0.0;sell_sum=0.0;last_side=0;switches=0
                    else:
                        fill=bid;eq=balance+liq;margin=open_n*((bid+ask)*0.5)/LEVERAGE;req=fill/LEVERAGE
                        if eq-margin<req:
                            failed=1; fail_i[0]=2; fail_i[1]=day; fail_i[2]=t; fail_i[3]=open_n; fail_i[4]=buy_n; fail_i[5]=sell_n; fail_i[6]=switches
                            fail_f[0]=balance; fail_f[1]=eq; fail_f[2]=bid; fail_f[3]=ask; fail_f[4]=liq
                        else:
                            if last_side==1:switches+=1
                            last_side=-1;sell_n+=1;sell_sum+=fill;open_n+=1;dn_outer=next_dn;g=gap_from_switches(switches);next_up=up_outer+g;next_dn=dn_outer-g
                            if en<len(ev_t):
                                ev_t[en]=t;ev_side[en]=-1;ev_fill[en]=fill;ev_pos[en]=open_n;ev_sw[en]=switches;ev_liq[en]=liq;ev_gap[en]=g;en+=1
                    acted=1
                if acted==0 or open_n==0 or failed!=0: break
            if open_n==0 and stopped==0 and day_realized>=TARGET:
                day_target=1;stopped=1;balance-=TARGET;withdrawn+=TARGET

        liq2=0.0
        if open_n>0: liq2=buy_n*bid-buy_sum+sell_sum-sell_n*ask-open_n*COMMISSION
        eq2=balance+liq2
        if eq2<min_eq:min_eq=eq2
        if eq2<=0.0 and failed==0:
            failed=1;fail_i[0]=3;fail_i[1]=day;fail_i[2]=t;fail_i[3]=open_n;fail_i[4]=buy_n;fail_i[5]=sell_n;fail_i[6]=switches
            fail_f[0]=balance;fail_f[1]=eq2;fail_f[2]=bid;fail_f[3]=ask;fail_f[4]=liq2
        last_bid=bid;last_ask=ask

    st_i[0]=initialized;st_i[1]=last_day;st_i[2]=sig_ptr;st_i[3]=open_n;st_i[4]=buy_n;st_i[5]=sell_n;st_i[6]=last_side;st_i[7]=switches
    st_i[8]=stopped;st_i[9]=day_activity;st_i[10]=day_target;st_i[11]=day_maxpos;st_i[12]=failed
    st_f[0]=balance;st_f[1]=withdrawn;st_f[2]=buy_sum;st_f[3]=sell_sum;st_f[4]=up_outer;st_f[5]=dn_outer;st_f[6]=next_up;st_f[7]=next_dn
    st_f[8]=day_realized;st_f[9]=last_bid;st_f[10]=last_ask;st_f[11]=min_eq
    ledger_n[0]=ln;ev_n[0]=en


def iso(day):
    return str(pd.Timestamp('1970-01-01',tz='UTC')+pd.Timedelta(days=int(day)))[:10]

def main():
    root=Path('compression_forensic');root.mkdir(exist_ok=True)
    zips=[];bars=[]
    for m in range(1,8):
        mm=f'{m:02d}'; fn=f'Exness_XAUUSD_Raw_Spread_2026_{mm}.zip'; p=root/fn
        url=f'https://ticks.ex2archive.com/ticks/XAUUSD_Raw_Spread/2026/{mm}/{fn}'
        print('DOWNLOAD',url,flush=True); download(url,p); zips.append((m,p)); bars.append(aggregate_zip_to_minutes(p,2026,m))
    allbars=pd.concat(bars,ignore_index=True).sort_values('minute').drop_duplicates('minute',keep='last').reset_index(drop=True)
    sig_t_all,sig_d_all,sig_n_all,_=build_signals(allbars)
    sig_n=int(sig_n_all[3]); sig_t=sig_t_all[3,:sig_n].copy();sig_d=sig_d_all[3,:sig_n].copy()
    print('COMPRESSION SIGNALS THROUGH JULY',sig_n,flush=True)

    st_i=np.array([0,-1,0,0,0,0,0,0,0,0,0,0,0],dtype=np.int64)
    st_f=np.zeros(12,dtype=np.float64);st_f[0]=START_BALANCE;st_f[11]=START_BALANCE
    ledger_day=np.full(300,-1,dtype=np.int64);ledger_pnl=np.zeros(300);ledger_target=np.zeros(300,dtype=np.int64);ledger_maxpos=np.zeros(300,dtype=np.int64);ledger_balance=np.zeros(300);ledger_withdrawn=np.zeros(300);ledger_n=np.array([0],dtype=np.int64)
    ev_t=np.full(10000,-1,dtype=np.int64);ev_side=np.zeros(10000,dtype=np.int64);ev_fill=np.zeros(10000);ev_pos=np.zeros(10000,dtype=np.int64);ev_sw=np.zeros(10000,dtype=np.int64);ev_liq=np.zeros(10000);ev_gap=np.zeros(10000);ev_n=np.array([0],dtype=np.int64)
    fail_i=np.full(7,-1,dtype=np.int64);fail_f=np.zeros(5)

    # warm compile
    replay(np.empty(0,dtype=np.int64),np.empty(0),np.empty(0),sig_t,sig_d,sig_n,st_i,st_f,ledger_day,ledger_pnl,ledger_target,ledger_maxpos,ledger_balance,ledger_withdrawn,ledger_n,ev_t,ev_side,ev_fill,ev_pos,ev_sw,ev_liq,ev_gap,ev_n,fail_i,fail_f)

    for m,p in zips:
        with zipfile.ZipFile(p) as z:
            for name in [x for x in z.namelist() if x.lower().endswith('.csv')]:
                with z.open(name) as fh:
                    for df in pd.read_csv(fh,usecols=['Timestamp','Bid','Ask'],chunksize=500_000):
                        t=pd.to_datetime(df.Timestamp,utc=True,errors='coerce');good=t.notna()&df.Bid.notna()&df.Ask.notna();df=df.loc[good];t=t.loc[good]
                        if len(df)==0:continue
                        replay(t.astype('int64').to_numpy(np.int64,copy=False),df.Bid.to_numpy(float,copy=False),df.Ask.to_numpy(float,copy=False),sig_t,sig_d,sig_n,st_i,st_f,ledger_day,ledger_pnl,ledger_target,ledger_maxpos,ledger_balance,ledger_withdrawn,ledger_n,ev_t,ev_side,ev_fill,ev_pos,ev_sw,ev_liq,ev_gap,ev_n,fail_i,fail_f)
        print('REPLAY',m,'failed=',st_i[12],flush=True)
        if st_i[12]: break

    # include failure/current day snapshot separately
    n=int(ledger_n[0]); ledger=[]
    for i in range(n): ledger.append({'date':iso(ledger_day[i]),'pnl':ledger_pnl[i],'target':int(ledger_target[i]),'max_positions':int(ledger_maxpos[i]),'balance_after_day':ledger_balance[i],'withdrawn_total':ledger_withdrawn[i]})
    pd.DataFrame(ledger).to_csv(root/'compression_daily_ledger_to_failure.csv',index=False)
    neg=[r for r in ledger if r['pnl']< -1e-9]
    print('NEGATIVE FINALIZED DAYS BEFORE FAILURE:',neg,flush=True)
    print('COUNTS before failure: traded',sum(1 for r in ledger if abs(r['pnl'])>1e-9 or r['max_positions']>0),'positive',sum(1 for r in ledger if r['pnl']>1e-9),'negative',len(neg),'targets',sum(r['target'] for r in ledger),flush=True)

    reason={1:'ENTRY_MARGIN',2:'ADD_MARGIN',3:'EQUITY_LE_ZERO'}.get(int(fail_i[0]),'NONE')
    ft=pd.Timestamp(int(fail_i[2]),tz='UTC') if fail_i[2]>0 else pd.NaT
    print('FAILURE',reason,'date',iso(fail_i[1]) if fail_i[1]>=0 else '', 'time',ft,flush=True)
    print('FAIL STATE balance',fail_f[0],'equity',fail_f[1],'bid',fail_f[2],'ask',fail_f[3],'floating_liq',fail_f[4],'open',fail_i[3],'buys',fail_i[4],'sells',fail_i[5],'switches',fail_i[6],'min_eq',st_f[11],'withdrawn',st_f[1],'day_realized',st_f[8],flush=True)

    fday=int(fail_i[1]); events=[]
    for i in range(int(ev_n[0])):
        d=int(ev_t[i]//86400000000000)
        if d==fday:
            events.append({'time':str(pd.Timestamp(int(ev_t[i]),tz='UTC')),'side':'BUY' if ev_side[i]>0 else 'SELL','fill':ev_fill[i],'positions_after':int(ev_pos[i]),'switches':int(ev_sw[i]),'liq_before_add':ev_liq[i],'next_gap':ev_gap[i]})
    pd.DataFrame(events).to_csv(root/'compression_failure_day_events.csv',index=False)
    print('FAILURE DAY ORDER EVENTS')
    for r in events: print(r,flush=True)

if __name__=='__main__':main()

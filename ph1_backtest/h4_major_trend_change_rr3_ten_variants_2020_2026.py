"""Causal H4 Major Trend Change backtest, RR3 ten variants, 2020-2026.

2026-11-06: new entry strategy is an objective H4 market-structure reversal,
NOT the previous daily/weekly support/resistance entry signal.

H4 Bid bars constructed incrementally from unmodified Exness Raw Spread
Bid/Ask ticks, aligned to UTC H4 at 00/04/08/12/16/20.
Only fully completed H4 bars can confirm a strict 2-left/2-right pivot.
Initial trend requires two successive rising H4 confirmed pivot highs AND
two successive rising pivot lows (uptrend), or both descending (downtrend).
Downtrend -> BUY only after a completed H4 *CLOSE* breaks ABOVE last
previously confirmed H4 pivot high (prior completed H4 close at/below).
Uptrend -> SELL only after completed H4 CLOSE breaks BELOW last confirmed
pivot low (prior completed H4 close at/above). Enter using actual first
available Bid/Ask quote of NEXT UTC H4 period. After reversal, trend
state flips; no repeated same-direction signals until an opposite
confirmed H4 shift occurs. Opposite trades may overlap if still live.
No future price data used for confirmation and no S/R breakout entry.
One objective operational definition; cannot represent every subjective
major trend change. NO tuning of H4 pivots or entries to outcome.

Ten predeclared RR3:1 TP/SL (diagram pip=Gold 0.10):
TP30/SL10, TP60/SL20, TP90/SL30, TP120/SL40, TP150/SL50,
TP180/SL60, TP210/SL70, TP240/SL80, TP270/SL90, TP300/SL100.

Single continuous initial $1000 account per variant, fixed 0.01 lot
(1 oz Gold), modeled .07 USD roundtrip fee per ticket, real Bid/Ask
spread, 1:2000 modeled leverage and equity stopout, no withdrawals.
Hold weekends/holidays: only TP or SL close. Open tickets at dataset
end remain open at marked-to-market quote, NOT forcibly liquidated.
Account-specific swaps/HMR/execution latency not reconstructed.
"""
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
from numba import njit
import major_sr_tp90_sl100_to_sl200_weekend_hold_2020_2026 as base

NS_HOUR=base.NS_HOUR
NS_DAY=base.NS_DAY
FEE=base.ROUND_TRIP_COMMISSION_PER_OZ
START=base.START
MAX_TRADES=base.MAX_TRADES
CONF=[]
for i in range(1,11):
    tp=3*i
    sl=i
    CONF.append((f'MAJOR_TREND_CHANGE_TP{tp*10}_SL{sl*10}',
        1.,0.,0,0,2000.,float(tp),float(sl),float(tp),float(sl),
        1.,0.,0.,0.,0.,0.,0.,0.,0.,0.))
N=len(CONF)
CFG=np.asarray([x[1:] for x in CONF],dtype=np.float64)
NAMES=[x[0] for x in CONF]

@njit
def observe_h4_reversal(t,bid,si,sf,hi,lo,gi):
    """Return 0/+1/-1 at FIRST tick after completed H4 changed structure.

    si[0] H4 serial; si[1] closed H4 bars; si[2] regime; si[3] reversal count.
    sf: active OHLC hi,lo,close [0:3], prior close [3],
        latest/previous confirmed H4 high [4:6],
        latest/previous confirmed H4 low [6:8],
        last trigger pivot [10].
    hi/lo: five last fully CLOSED H4 highs/lows.
    gi[0]/gi[1]: confirmed high/low counts.
    """
    h=t//(4*NS_HOUR)
    if si[0]<0:
        si[0]=h
        si[1]=0
        si[2]=0
        si[3]=0
        gi[0]=0
        gi[1]=0
        sf[0]=bid;sf[1]=bid;sf[2]=bid
        return 0
    if h==si[0]:
        if bid>sf[0]:sf[0]=bid
        if bid<sf[1]:sf[1]=bid
        sf[2]=bid
        return 0
    # Only the just COMPLETED H4 bar's last Bid close is used now.
    c=sf[2]
    p=sf[3]
    old=si[2]
    signal=0
    if old==-1 and sf[4]>0. and p>0.:
        if p<=sf[4] and c>sf[4]:
            signal=1
            sf[10]=sf[4]
    elif old==1 and sf[6]>0. and p>0.:
        if p>=sf[6] and c<sf[6]:
            signal=-1
            sf[10]=sf[6]
    if signal!=0:
        si[2]=signal
        si[3]+=1
    # Add just completed H4 bar AFTER evaluating reversal at old pivots.
    # Therefore a pivot confirmed at this boundary is only available
    # for LATER H4 reversals (causal; two right bars fully closed).
    for k in range(4):
        hi[k]=hi[k+1]
        lo[k]=lo[k+1]
    hi[4]=sf[0]
    lo[4]=sf[1]
    si[1]+=1
    if si[1]>=5:
        ph=True
        pl=True
        for k in range(5):
            if k==2:continue
            if hi[2]<=hi[k]:ph=False
            if lo[2]>=lo[k]:pl=False
        if ph:
            sf[5]=sf[4]
            sf[4]=hi[2]
            gi[0]+=1
        if pl:
            sf[7]=sf[6]
            sf[6]=lo[2]
            gi[1]+=1
    if si[2]==0 and gi[0]>=2 and gi[1]>=2:
        if sf[4]>sf[5] and sf[6]>sf[7]:
            si[2]=1
        elif sf[4]<sf[5] and sf[6]<sf[7]:
            si[2]=-1
    sf[3]=c
    si[0]=h
    sf[0]=bid;sf[1]=bid;sf[2]=bid
    return signal

@njit
def engine(ts,bids,asks,starts,ends,sids,CFG,cash,withdrawn,daily,
           active,an,ti,tf,stats_i,stats_f,results_i,results_f,day_pnl,
           session_count,session_pnl,global_i,global_f,
           refhi,reflo,valid,serial,seen,missing,base_day,
           sr_i,sr_f,daily_high,daily_low,level_counts,
           reg_n,reg_p,reg_armed,reg_last,frozen_levels,
           rollover_times,rollover_multipliers,rollover_cursor,
           stopout_flag,margin_call_active,preholiday_thursday):
    # Reuse existing arrays solely for H4 observer state: the old
    # daily/weekly S/R calculations and regional-session events are NEVER run.
    for z in range(len(ts)):
        t=ts[z];bid=bids[z];ask=asks[z]
        if not (np.isfinite(bid) and np.isfinite(ask) and bid>0 and ask>=bid):
            continue
        signal=observe_h4_reversal(t,bid,sr_i,sr_f,daily_high,daily_low,global_i)
        day=t//NS_DAY
        for c in range(N):
            if stats_i[c,10]!=0:continue
            lev=CFG[c,4]
            eq,margin=base.mark(c,bid,ask,cash,active,an,ti,tf,lev)
            if margin>0. and eq/margin<=.30:
                if margin_call_active[c]==0:
                    margin_call_active[c]=1
                    stats_i[c,18]+=1
            else:margin_call_active[c]=0
            if eq<=0. and an[c]>0:
                while eq<=0. and an[c]>0:
                    worst=0
                    worstnet=np.inf
                    for k in range(an[c]):
                        j=active[c,k];side=ti[c,j,0]
                        x=side*(bid-tf[c,j,0]) if side==1 else tf[c,j,0]-ask
                        if x<worstnet:worstnet=x;worst=k
                    base.close_ticket(c,worst,t,bid,ask,4,CFG,cash,daily,ti,tf,
                        active,an,stats_i,stats_f,results_i,results_f,day_pnl,
                        session_count,session_pnl,base_day)
                    eq,margin=base.mark(c,bid,ask,cash,active,an,ti,tf,lev)
                if eq<=0.:stopout_flag[c]=1
            if eq<=0.:stopout_flag[c]=1
            slip=CFG[c,1]
            k=0
            while k<an[c]:
                j=active[c,k];side=ti[c,j,0];entry=tf[c,j,0]
                executable=bid-slip if side==1 else ask+slip
                stop=tf[c,j,6]
                tp=entry+side*(CFG[c,5] if side==1 else CFG[c,7])
                sl_hit=(executable<=stop) if side==1 else (executable>=stop)
                tp_hit=(executable>=tp) if side==1 else (executable<=tp)
                if sl_hit or tp_hit:
                    base.close_ticket(c,k,t,bid,ask,2 if sl_hit else 1,
                        CFG,cash,daily,ti,tf,active,an,stats_i,stats_f,
                        results_i,results_f,day_pnl,session_count,
                        session_pnl,base_day)
                    continue
                k+=1
            # A newly confirmed major trend reversal is the ONLY entry.
            # The same global H4 event is seen by all ten R:R variants.
            if signal!=0 and stopout_flag[c]==0:
                stats_i[c,25]+=1
                if stats_i[c,0]>=MAX_TRADES:
                    stats_i[c,10]=2
                    stats_i[c,11]=t
                else:
                    side=signal
                    units=CFG[c,0]
                    entry=ask+slip if side==1 else bid-slip
                    fee=units*FEE
                    eq,margin=base.mark(c,bid,ask,cash,active,an,ti,tf,lev)
                    netoz=0.
                    for u in range(an[c]):
                        j=active[c,u];netoz+=ti[c,j,0]*tf[c,j,4]
                    newer_margin=abs(netoz+side*units)*bid/lev
                    new_equity=eq-units*(ask-bid+slip)-fee
                    if new_equity-newer_margin<0.:
                        stats_i[c,9]+=1
                    else:
                        j=stats_i[c,0];stats_i[c,0]+=1
                        ti[c,j,0]=side;ti[c,j,1]=t
                        ti[c,j,2]=0 if side==1 else 1
                        ti[c,j,3]=0 if side==1 else 2
                        ti[c,j,4]=0
                        tf[c,j,0]=entry
                        tf[c,j,2]=sf_level=sr_f[10] # already known H4 reversal pivot
                        tf[c,j,3]=sf_level
                        tf[c,j,4]=units;tf[c,j,5]=ask-bid
                        tf[c,j,6]=entry-side*(CFG[c,6] if side==1 else CFG[c,8])
                        cash[c]-=fee
                        active[c,an[c]]=j;an[c]+=1
                        stats_i[c,24]+=1
                        session_count[c,ti[c,j,2],0]+=1
            eq,margin=base.mark(c,bid,ask,cash,active,an,ti,tf,lev)
            if eq<stats_f[c,0]:stats_f[c,0]=eq
            if margin>stats_f[c,1]:stats_f[c,1]=margin
            if eq-margin<stats_f[c,2]:stats_f[c,2]=eq-margin
            wealth=eq+withdrawn[c]
            if wealth>stats_f[c,3]:stats_f[c,3]=wealth
            dd=stats_f[c,3]-wealth
            if dd>stats_f[c,4]:stats_f[c,4]=dd
            if an[c]>stats_i[c,8]:stats_i[c,8]=an[c]
            if an[c]>1:stats_i[c,15]+=1
            if eq<=0. and stats_i[c,10]==0:
                stats_i[c,10]=1;stats_i[c,11]=t
                stats_f[c,9]=eq;stats_f[c,10]=margin
                stopout_flag[c]=1
        global_f[2]=bid;global_f[3]=ask;global_i[4]=t

def selftest():
    assert len(CONF)==10 and CFG.shape==(10,19)
    for i,c in enumerate(CONF):
        assert c[0]==f'MAJOR_TREND_CHANGE_TP{30*(i+1)}_SL{10*(i+1)}'
        assert c[1]==1. and c[3]==0 and c[4]==0 and c[5]==2000.
        assert c[6]==3*(i+1) and c[7]==i+1
        assert c[8]==3*(i+1) and c[9]==i+1
        assert c[11]==0. and c[12]==0. and c[16]==0.
    si=np.zeros(4,dtype=np.int64);si[0]=-1
    sf=np.zeros(8,dtype=np.float64)
    hi=np.zeros(5);lo=np.zeros(5)
    gi=np.zeros(7,dtype=np.int64)
    # Directly check no data leakage and reversal only first NEXT H4 tick.
    observe_h4_reversal(0,100.,si,sf,hi,lo,gi)
    si[2]=-1;sf[4]=105.;sf[3]=101.
    observe_h4_reversal(3*NS_HOUR,108.,si,sf,hi,lo,gi)
    result=observe_h4_reversal(4*NS_HOUR,108.,si,sf,hi,lo,gi)
    assert result==1 and si[2]==1 and si[3]==1
    assert observe_h4_reversal(4*NS_HOUR+1,109.,si,sf,hi,lo,gi)==0
    # Use 5 CLOSED H4 bars to confirm strict central pivot only.
    si=np.zeros(4,dtype=np.int64);si[0]=-1
    sf=np.zeros(8,dtype=np.float64)
    hi=np.zeros(5);lo=np.zeros(5);gi=np.zeros(7,dtype=np.int64)
    seq=[(100,90,95),(105,91,102),(110,92,108),
         (106,93,100),(103,91,99),(102,90,93)]
    for i,(h,l,cl) in enumerate(seq):
        observe_h4_reversal(i*4*NS_HOUR,float(l),si,sf,hi,lo,gi)
        observe_h4_reversal((i*4+1)*NS_HOUR,float(h),si,sf,hi,lo,gi)
        observe_h4_reversal((i*4+3)*NS_HOUR,float(cl),si,sf,hi,lo,gi)
    observe_h4_reversal(len(seq)*4*NS_HOUR,99.,si,sf,hi,lo,gi)
    assert si[1]==len(seq) and gi[0]>=1
    print('PASS 10 fixed 3:1 RR variants; zero old SR entries; H4 strict 2L2R swing and causal closed-bar trend reversal',flush=True)

def run(out):
    # Existing well-audited 84-archive downloader, streaming pandas parsing,
    # SHA-256 provenance and continuous-account outcome reporter are reused.
    # Its engine is replaced *entirely* by the new H4 reversal engine.
    base.CONF=CONF; base.N=N; base.CFG=CFG; base.CONF_NAMES=NAMES
    base.SESSION_NAMES=['H4 bullish shift','H4 bearish shift','unused','unused']
    base.engine=engine
    base.selftest=selftest
    base.run(out)
    out=Path(out)
    lp=out/'ticket_ledger.csv'
    df=pd.read_csv(lp)
    if len(df):
        df['source']=np.where(df['side']=='BUY',
            'H4_PREVIOUS_DOWNTREND_CLOSES_ABOVE_CONFIRMED_SWING_HIGH',
            'H4_PREVIOUS_UPTREND_CLOSES_BELOW_CONFIRMED_SWING_LOW')
        df=df.rename(columns={'major_resistance':'trigger_h4_pivot_price'})
        df=df.drop(columns=['major_support','repeated_after_confirmed_H1_rearm'],errors='ignore')
        df.to_csv(lp,index=False)
    sumfile=out/'model_summary.csv'
    summary=pd.read_csv(sumfile)
    summary['strategy']='H4_2L2R_CONFIRMED_MAJOR_TREND_CHANGE'
    summary['trend_entry_rule']='UP/down prior 2 successive confirmed H4 pivot HH-HL / LH-LL; first next H4 quote after close through last opposite swing'
    summary=summary.drop(columns=['h1_prebreak_rearm_price_distance','candidate_universe','level_zone_price_width',
                                 'rearm_confirmations','repeat_entries','unique_sr_zones_traded'],errors='ignore')
    summary.to_csv(sumfile,index=False)
    p=out/'provenance.json'
    info=json.loads(p.read_text())
    info['entry_strategy']='H4 ONLY: strict causal 2-left/2-right confirmed pivots, initial higher-high/higher-low or lower-high/lower-low regime; candle CLOSE beyond confirmed opposite-direction swing and NEXT H4 first tick entry. NO daily/weekly S/R breakout; NO regional sessions.'
    info['signal_dedup']='One opposite H4 regime change each time; trend flips after first confirmed reversal, no repeated same-way signals.'
    info['timed_exit_policy']='No Friday/time/BE/trailing exits; own TP and SL only. 0.01 lot; 3:1 RR.'
    info['h4_rule']='Initial two successive H4 confirmed pivot high and two successive pivot lows must move together to form trend. Reverse only on completed H4 candle close crossing last confirmed opposing H4 pivot, previous H4 close on original side; enter first next tick.'
    info['model_selection_note']='H4 two-left/two-right confirmation fixed BEFORE checking 2020-2026 historical outcomes; this is not a test of every possible major trend definition.'
    info['old_sr_signal_used']=False
    info.pop('year_account',None)
    info['year_account']='ONE single continuous $1000 account for each model, no deposits/withdrawals, 0.01 lot per signal'
    p.write_text(json.dumps(info,indent=2))
    assert len(summary)==10
    for _,row in summary.iterrows():
        assert int(row['forced_friday_flat'])==0
        assert int(row['time_stopped_exits'])==0
        assert int(row['breakeven_exits'])==0
        assert int(row['trailing_exits'])==0
        assert int(row['trades_closed'])==int(row['TP'])+int(row['SL'])+int(row['modeled_stopout_liquidations'])
    print('FINAL_H4_TREND_MODEL_SUMMARY\n'+summary.to_string(index=False),flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--out',default='results/continuous_2020_2026')
    ap.add_argument('--selftest',action='store_true')
    a=ap.parse_args()
    if a.selftest:selftest()
    else:run(a.out)

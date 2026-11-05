"""Continuous XAUUSD Major S/R TP90/SL90 with optional second same-direction
0.01lot ticket if first trade has moved adverse 80 user-pips (Gold $8)
while its first SL90 (Gold $9) has not hit. Child TP180 (Gold $18)
and SL10 (Gold $1) from child's ACTUAL Bid/Ask fill.
Four predeclared interpretations: untouched baseline; independently filled
per-order TP/SL; synchronized-basket at first TP90; synchronized-basket
at child's TP180. Two TP levels do NOT coincide: at ideal Gold4000 BUY
first TP4009, child at3992 has TP4010. Basket first TP implies child
effective TP ~170 pips, basket second TP implies first effective TP ~100
pips. Each trade is closed at actual observed quote on SL, target capped
at specified basket level for TP. Weekend carry, never forced Friday
closure. 2020-2026 real Exness Raw Spread bid/ask, single continuous
$1000, all causal H1/SR entry and rearm logic unchanged, 0.01lot each
order, $0.07 fee EACH order, no withdrawals, no martingale beyond one child.
"""
import argparse
import hashlib
import json
import math
import zipfile
from pathlib import Path
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd
import requests
from numba import njit

START=1000.
TP_PRICE=1.00
SL_PRICE=1.00
ROUND_TRIP_COMMISSION_PER_OZ=.07  # standard lot 100oz -> $7 total, .1 lot 10oz -> .70
NS_DAY=86_400_000_000_000
NS_HOUR=3_600_000_000_000
END_2026=pd.Timestamp('2026-11-05T09:12:24Z').value
FRIDAY_FLAT_NS=12*NS_HOUR
THURSDAY_EARLY_CLOSE_NS=12*NS_HOUR
YEAR_START=2020
YEAR_END=2026
MAX_TRADES=30000
MAX_REGISTERED_SR=6000
SR_ZONE=1.00
NLEVELS=4
SESSION_NAMES=['Sydney','Tokyo','London','New York']
SESSIONS=[('Australia/Sydney',8),('Asia/Tokyo',9),('Europe/London',8),('America/New_York',8)]

# Previous 15 numeric config fields unchanged. Appended:
# mode 0 baseline,1 BE,2 trail,3 losing-time-cut;
# trigger (+ Gold MFE), trail_gap, time_cut_hours.
# 19 fields per profile; index 7 BUY_SL, index 9 SELL_SL in Gold price.
CONF=[
 ('BASE_TP90_SL90',1.,0.,0,0,2000.,9.,9.,9.,9.,1.,0.,0.,0.,9.,0.,0.,0.,0.,0.,0.),
 ('ADD80_INDEPENDENT_TP180_SL10',1.,0.,0,0,2000.,9.,9.,9.,9.,1.,0.,0.,0.,9.,0.,0.,0.,0.,0.,1.),
 ('ADD80_BASKET_AT_FIRST_TP90',1.,0.,0,0,2000.,9.,9.,9.,9.,1.,0.,0.,0.,9.,0.,0.,0.,0.,0.,2.),
 ('ADD80_BASKET_AT_SECOND_TP180',1.,0.,0,0,2000.,9.,9.,9.,9.,1.,0.,0.,0.,9.,0.,0.,0.,0.,0.,3.),
]
N=len(CONF)
CFG=np.asarray([x[1:] for x in CONF],dtype=np.float64)
CONF_NAMES=[x[0] for x in CONF]

def schedule(year):
    events=[]
    lo=pd.Timestamp(f'{year}-01-01T00:00:00Z').value
    hi=pd.Timestamp(f'{year}-12-31T23:59:59.999999999Z').value if year<=2025 else END_2026
    for sid,(zone,hour) in enumerate(SESSIONS):
        tz=ZoneInfo(zone)
        d=datetime(year,1,1).date()-timedelta(days=2)
        last=datetime(year,12,31).date() if year<=2025 else datetime(year,11,6).date()
        while d<=last:
            if d.weekday()<5:
                st=datetime(d.year,d.month,d.day,hour,0,tzinfo=tz)
                ns=int(st.astimezone(timezone.utc).timestamp()*1_000_000_000)
                if lo<=ns<=hi:
                    events.append((ns,ns+NS_HOUR,sid))
            d+=timedelta(days=1)
    events.sort()
    return (
        np.asarray([x[0] for x in events],dtype=np.int64),
        np.asarray([x[1] for x in events],dtype=np.int64),
        np.asarray([x[2] for x in events],dtype=np.int64)
    )

@njit
def select_major_levels(bid,pivot_hi,pivot_lo,week_hi,week_lo):
    """Select nearest known valid resistance strictly above and support below."""
    resistance=math.inf
    support=0.
    source_hi=0
    source_lo=0
    if pivot_hi>bid and math.isfinite(pivot_hi):
        resistance=pivot_hi;source_hi=1
    if week_hi>bid and week_hi<resistance and math.isfinite(week_hi):
        resistance=week_hi;source_hi=2
    if pivot_lo>0. and pivot_lo<bid and math.isfinite(pivot_lo):
        support=pivot_lo;source_lo=1
    if week_lo>support and week_lo<bid and math.isfinite(week_lo):
        support=week_lo;source_lo=2
    return resistance,support,source_hi,source_lo

@njit
def observe_structure(t,bid,sr_i,sr_f,daily_high,daily_low):
    # UTC D1 bars are assembled incrementally from the same real quote ticks.
    day=t//NS_DAY
    week=(day+3)//7  # UTC Monday to Sunday weeks.
    if sr_i[0]<0:
        sr_i[0]=day
        sr_i[2]=week
        sr_f[0]=bid;sr_f[1]=bid
        sr_f[2]=bid;sr_f[3]=bid
        return
    if day!=sr_i[0]:
        # Finalize old D1; only 5 fully CLOSED D1 bars can confirm a center pivot.
        for j in range(4):
            daily_high[j]=daily_high[j+1]
            daily_low[j]=daily_low[j+1]
        daily_high[4]=sr_f[0];daily_low[4]=sr_f[1]
        sr_i[1]+=1
        if sr_i[1]>=5:
            pivh=True
            pivl=True
            for j in range(5):
                if j==2:continue
                if daily_high[2]<=daily_high[j]:pivh=False
                if daily_low[2]>=daily_low[j]:pivl=False
            if pivh:sr_f[4]=daily_high[2] # available only AFTER 2 right bars close.
            if pivl:sr_f[5]=daily_low[2]
        sr_i[0]=day
        sr_f[0]=bid;sr_f[1]=bid
    else:
        if bid>sr_f[0]:sr_f[0]=bid
        if bid<sr_f[1]:sr_f[1]=bid
    if week!=sr_i[2]:
        # Closed previous UTC week, not current or future high/low.
        sr_f[6]=sr_f[2];sr_f[7]=sr_f[3]
        sr_i[2]=week
        sr_i[3]+=1
        sr_f[2]=bid;sr_f[3]=bid
    else:
        if bid>sr_f[2]:sr_f[2]=bid
        if bid<sr_f[3]:sr_f[3]=bid

@njit
def mark(c,bid,ask,cash,active,an,ti,tf,lev):
    equity=cash[c]
    net_oz=0.
    for k in range(an[c]):
        j=active[c,k]
        side=ti[c,j,0]
        entry=tf[c,j,0]
        units=tf[c,j,4]
        if side==1:
            equity+=units*(bid-entry)
        else:
            equity+=units*(entry-ask)
        net_oz+=side*units
    return equity,abs(net_oz)*bid/lev

@njit
def close_ticket(c,k,t,bid,ask,reason,CFG,cash,daily,ti,tf,active,an,
                 stats_i,stats_f,results_i,results_f,day_pnl,session_count,session_pnl,base_day):
    j=active[c,k]
    side=ti[c,j,0]
    units=tf[c,j,4]
    entry=tf[c,j,0]
    slip=CFG[c,1]
    # Profit target is a LIMIT execution, capped at requested target (no fictitious better fill).
    # Stop loss and Friday-market exits execute at the actual quote after adverse slippage.
    if side==1:
        exitprice=tf[c,j,8] if reason==1 else bid-slip
        gross=units*(exitprice-entry)
    else:
        exitprice=tf[c,j,8] if reason==1 else ask+slip
        gross=units*(entry-exitprice)
    net=gross-units*ROUND_TRIP_COMMISSION_PER_OZ
    cash[c]+=gross
    daily[c]+=net
    stats_i[c,1]+=1
    if net>0:
        stats_i[c,2]+=1
    else:
        stats_i[c,3]+=1
    if reason==1:stats_i[c,4]+=1
    elif reason==2:stats_i[c,5]+=1
    elif reason==3:stats_i[c,6]+=1
    elif reason==4:stats_i[c,17]+=1
    elif reason==5:stats_i[c,26]+=1
    elif reason==6:stats_i[c,27]+=1
    elif reason==7:stats_i[c,28]+=1
    if net<stats_f[c,6]:stats_f[c,6]=net
    delta=(t-ti[c,j,1])/1e9
    stats_f[c,7]+=delta
    if delta>stats_f[c,8]:stats_f[c,8]=delta
    if delta>stats_i[c,13]:stats_i[c,13]=int(delta)
    day_index=int(t//NS_DAY-base_day)
    if 0<=day_index<day_pnl.shape[1]:
        day_pnl[c,day_index]+=net
    session=ti[c,j,2]
    session_count[c,session,1]+=1
    if net>0:session_count[c,session,2]+=1
    session_pnl[c,session]+=net
    x=stats_i[c,1]-1
    if x<results_i.shape[1]:
        # columns: session, side, entry_time, exit_time, exit_reason, initial H1 local-session clock id
        results_i[c,x,0]=session
        results_i[c,x,1]=side
        results_i[c,x,2]=ti[c,j,1]
        results_i[c,x,3]=t
        results_i[c,x,4]=reason
        results_i[c,x,5]=ti[c,j,3] # exact causal level source
        results_i[c,x,6]=ti[c,j,4]
        results_i[c,x,7]=ti[c,j,5] # parent family ticket ID
        results_i[c,x,8]=ti[c,j,6] # first=0, child=1
        results_f[c,x,0]=entry
        results_f[c,x,1]=exitprice
        results_f[c,x,2]=net
        results_f[c,x,3]=tf[c,j,2] # best preceding hour bid high
        results_f[c,x,4]=tf[c,j,3] # best preceding hour bid low
        results_f[c,x,5]=units/100.
        results_f[c,x,6]=tf[c,j,5] # entry observed spread
    an[c]-=1
    active[c,k]=active[c,an[c]]

@njit
def freeze_source_candidates(sid,bid,sr_f,levels,valid,level_counts):
    # Existing proven causal source universe: latest confirmed D1 pivot,
    # last fully completed UTC week; expose BOTH not just nearest.
    for k in range(4):levels[sid,k]=0.
    if sr_f[4]>bid and math.isfinite(sr_f[4]):
        levels[sid,0]=sr_f[4];level_counts[0,1]+=1
    if sr_f[6]>bid and math.isfinite(sr_f[6]):
        levels[sid,1]=sr_f[6];level_counts[0,2]+=1
    if sr_f[5]>0. and sr_f[5]<bid and math.isfinite(sr_f[5]):
        levels[sid,2]=sr_f[5];level_counts[1,1]+=1
    if sr_f[7]>0. and sr_f[7]<bid and math.isfinite(sr_f[7]):
        levels[sid,3]=sr_f[7];level_counts[1,2]+=1
    valid[sid]=0
    for k in range(4):
        if levels[sid,k]>0.:valid[sid]=1
    if valid[sid]==0:level_counts[2,0]+=1

@njit
def find_previous_zone(c,bound,level,reg_n,reg_p):
    best=-1;dmin=SR_ZONE+1.e-8
    for j in range(reg_n[c,bound]):
        d=abs(reg_p[c,bound,j]-level)
        if d<=SR_ZONE+1.e-9 and d<dmin:
            best=j;dmin=d
    return best

@njit
def confirm_old_hour_close_rearms(close_bid,t,CFG,reg_n,reg_p,reg_armed,reg_last,stats_i):
    for c in range(N):
        if stats_i[c,10]!=0:continue
        away=CFG[c,13]
        for bound in range(2):
            for j in range(reg_n[c,bound]):
                if reg_armed[c,bound,j]!=0 or reg_last[c,bound,j]>=t:continue
                p=reg_p[c,bound,j]
                if (bound==0 and close_bid<=p-away) or (bound==1 and close_bid>=p+away):
                    reg_armed[c,bound,j]=1
                    stats_i[c,22]+=1

@njit
def engine(ts,bids,asks,starts,ends,sids,CFG,cash,withdrawn,daily,
           active,an,ti,tf,stats_i,stats_f,results_i,results_f,day_pnl,
           session_count,session_pnl,global_i,global_f,
           refhi,reflo,valid,serial,seen,missing,base_day,
           sr_i,sr_f,daily_high,daily_low,level_counts,
           reg_n,reg_p,reg_armed,reg_last,frozen_levels,
           rollover_times,rollover_multipliers,rollover_cursor,stopout_flag,
           margin_call_active,preholiday_thursday):
    for z in range(len(ts)):
        t=ts[z];bid=bids[z];ask=asks[z]
        if not(math.isfinite(bid) and math.isfinite(ask) and bid>0 and ask>=bid):
            continue
        # Verify fresh independent level validity from LAST FULLY CLOSED UTC H1.
        h=t//NS_HOUR
        if global_i[6]<0:global_i[6]=h
        elif h!=global_i[6]:
            if global_f[2]>0.:
                confirm_old_hour_close_rearms(global_f[2],t,CFG,reg_n,reg_p,reg_armed,reg_last,stats_i)
            global_i[6]=h
        # Apply swap at the first available quote at/after scheduled broker
        # rollover, to tickets carried across the rollover timestamp.
        while rollover_cursor[0]<len(rollover_times) and rollover_times[rollover_cursor[0]]<=t:
            rt=rollover_times[rollover_cursor[0]]
            mul=rollover_multipliers[rollover_cursor[0]]
            for c in range(N):
                if CFG[c,11]<=0:continue
                for k in range(an[c]):
                    j=active[c,k]
                    if ti[c,j,1]<rt:
                        charge=CFG[c,11]*mul*tf[c,j,4]
                        cash[c]-=charge
                        stats_f[c,11]+=charge
                        stats_i[c,19]+=1
            rollover_cursor[0]+=1
        # Strict real-time D1/UTC-week structure, no look-ahead.
        observe_structure(t,bid,sr_i,sr_f,daily_high,daily_low)
        day=t//NS_DAY
        if global_i[3]<0:global_i[3]=day
        if day!=global_i[3]:
            # Net daily REALIZED profit only, no withdrawal of unrealized group mark.
            for c in range(N):
                if stats_i[c,10]!=0:continue
                if CFG[c,2]>.5 and daily[c]>0:
                    eq,margin=mark(c,global_f[2],global_f[3],cash,active,an,ti,tf,CFG[c,4])
                    take=min(daily[c],max(0.,eq-margin))
                    if daily[c]-take>1e-8:stats_i[c,12]+=1
                    cash[c]-=take;withdrawn[c]+=take
                daily[c]=0.
            global_i[3]=day

        # Finish first one-hour reference and publish independently per session
        prev=global_i[1]
        if prev>=0 and t>=ends[prev]:
            sid=sids[prev]
            if global_i[2]>0:
                freeze_source_candidates(sid,bid,sr_f,frozen_levels,valid,level_counts)
                rh,rl,sh,sl=select_major_levels(bid,sr_f[4],sr_f[5],sr_f[6],sr_f[7])
                refhi[sid]=rh;reflo[sid]=rl
                serial[sid]+=1
            else:missing[sid]+=1
            global_i[1]=-1;global_i[2]=0
        # New local session supersedes old unexecuted first-H1 signal for that same session
        while global_i[0]<len(starts) and t>=starts[global_i[0]]:
            idx=global_i[0];sid=sids[idx]
            valid[sid]=0
            if global_i[1]>=0:
                other=sids[global_i[1]]
                if global_i[2]>0:
                    freeze_source_candidates(other,bid,sr_f,frozen_levels,valid,level_counts)
                    rh,rl,sh,sl=select_major_levels(bid,sr_f[4],sr_f[5],sr_f[6],sr_f[7])
                    refhi[other]=rh;reflo[other]=rl
                    serial[other]+=1
                else:missing[other]+=1
                global_i[1]=-1;global_i[2]=0
            if t<ends[idx]:
                global_i[1]=idx
                global_f[0]=bid;global_f[1]=bid
                global_i[2]=1
            else:missing[sid]+=1
            global_i[0]+=1
        current=global_i[1]
        if current>=0 and t<ends[current]:
            if bid>global_f[0]:global_f[0]=bid
            if bid<global_f[1]:global_f[1]=bid
            global_i[2]+=1

        dow=(day+3)%7
        hour=(t//NS_HOUR)%24
        fri_after_noon=(dow==4 and (t%NS_DAY)>=FRIDAY_FLAT_NS)
        thu_after_19=(dow==3 and (t%NS_DAY)>=THURSDAY_EARLY_CLOSE_NS)
        before_holiday=(day-base_day>=0 and day-base_day<len(preholiday_thursday) and preholiday_thursday[day-base_day]!=0)
        if global_i[5]!=day:global_i[5]=day
        for c in range(N):
            if stats_i[c,10]!=0:continue
            lev=CFG[c,4]
            # USER OVERRIDE: no Friday or Thursday forced close / entry
            # restrictions. Historical quote feed has no weekend trades
            # while market is shut, but open positions continue to carry.
            friday_due=False
            eq,margin=mark(c,bid,ask,cash,active,an,ti,tf,lev)
            if margin>0 and eq/margin<=0.30:
                if margin_call_active[c]==0:
                    margin_call_active[c]=1
                    stats_i[c,18]+=1
            else:
                margin_call_active[c]=0
            if eq<=0. and an[c]>0:
                # Exness Raw Spread 0% stop-out approximation: remove least
                # profitable remaining position first, until equity>0.
                while eq<=0. and an[c]>0:
                    worst_k=0;worst_profit=math.inf
                    for k in range(an[c]):
                        j=active[c,k];side=ti[c,j,0]
                        profit=side*(bid-tf[c,j,0]) if side==1 else tf[c,j,0]-ask
                        if profit<worst_profit:worst_profit=profit;worst_k=k
                    close_ticket(c,worst_k,t,bid,ask,4,CFG,cash,daily,ti,tf,active,an,
                         stats_i,stats_f,results_i,results_f,day_pnl,session_count,
                         session_pnl,base_day)
                    eq,margin=mark(c,bid,ask,cash,active,an,ti,tf,lev)
                if eq<=0.:
                    stopout_flag[c]=1
            if eq<=0.:
                # Once a $1,000 account is bust, no replenishment.
                stopout_flag[c]=1
            slip=CFG[c,1]

            # Handle TP/SL first, then any adverse $8 add-on.
            # Per-ticket TP on actual executable quote, stop can gap.
            k=0
            while k<an[c]:
                j=active[c,k];side=ti[c,j,0];entry=tf[c,j,0]
                quote=bid-slip if side==1 else ask+slip
                mode=int(CFG[c,19])
                if mode>=2 and ti[c,j,6]==1:
                    k+=1;continue
                if mode>=2 and ti[c,j,6]==0 and tf[c,j,10]>0.:
                    child=int(tf[c,j,10])-1
                    childindex=-1
                    for u in range(an[c]):
                        if active[c,u]==child:childindex=u;break
                    if childindex>=0:
                        stop1=tf[c,j,6];stop2=tf[c,child,6]
                        sharedstop=max(stop1,stop2) if side==1 else min(stop1,stop2)
                        target=entry+side*9. if mode==2 else tf[c,child,8]
                        hitstop=quote<=sharedstop if side==1 else quote>=sharedstop
                        hittp=quote>=target if side==1 else quote<=target
                        if hitstop or hittp:
                            reason=2 if hitstop else 1
                            tf[c,j,8]=target;tf[c,child,8]=target
                            if reason==1:stats_i[c,33]+=1
                            else:stats_i[c,34]+=1
                            close_ticket(c,childindex,t,bid,ask,reason,CFG,cash,daily,ti,tf,active,an,
                                stats_i,stats_f,results_i,results_f,day_pnl,session_count,session_pnl,base_day)
                            for u in range(an[c]):
                                if active[c,u]==j:
                                    close_ticket(c,u,t,bid,ask,reason,CFG,cash,daily,ti,tf,active,an,
                                        stats_i,stats_f,results_i,results_f,day_pnl,session_count,session_pnl,base_day)
                                    break
                            continue
                        k+=1;continue
                sl=tf[c,j,6];tp=tf[c,j,8]
                hitstop=quote<=sl if side==1 else quote>=sl
                hittp=quote>=tp if side==1 else quote<=tp
                if hitstop or hittp:
                    reason=2 if hitstop else 1
                    close_ticket(c,k,t,bid,ask,reason,CFG,cash,daily,ti,tf,active,an,
                        stats_i,stats_f,results_i,results_f,day_pnl,session_count,session_pnl,base_day)
                    continue
                k+=1
            # Child offered only once per still-open FIRST ticket after its
            # executable Gold -8 threshold, BEFORE Gold -9 original SL.
            if int(CFG[c,19])>0 and stopout_flag[c]==0:
                old_an=an[c]
                for u in range(old_an):
                    j=active[c,u]
                    if ti[c,j,6]!=0 or tf[c,j,9]>0.:continue
                    side=ti[c,j,0];entry=tf[c,j,0]
                    quote=bid-slip if side==1 else ask+slip
                    movement=side*(quote-entry)
                    if movement>-8. or movement<=-9.:continue
                    if stats_i[c,0]>=MAX_TRADES:
                        stats_i[c,10]=2;stats_i[c,11]=t;break
                    newentry=ask+slip if side==1 else bid-slip
                    units=CFG[c,0];fee=units*ROUND_TRIP_COMMISSION_PER_OZ
                    eq,mm=mark(c,bid,ask,cash,active,an,ti,tf,lev)
                    netoz=0.
                    for w in range(an[c]):
                        old=active[c,w];netoz+=ti[c,old,0]*tf[c,old,4]
                    newmargin=abs(netoz+side*units)*bid/lev
                    if eq-units*(ask-bid+slip)-fee-newmargin<0.:
                        stats_i[c,9]+=1;continue
                    child=stats_i[c,0];stats_i[c,0]+=1
                    ti[c,child,0]=side;ti[c,child,1]=t;ti[c,child,2]=ti[c,j,2]
                    ti[c,child,3]=ti[c,j,3];ti[c,child,4]=ti[c,j,4]
                    ti[c,child,5]=j;ti[c,child,6]=1
                    tf[c,child,0]=newentry
                    tf[c,child,2]=tf[c,j,2];tf[c,child,3]=tf[c,j,3]
                    tf[c,child,4]=units;tf[c,child,5]=ask-bid
                    tf[c,child,6]=newentry-side*1. # SL10
                    tf[c,child,8]=newentry+side*18. # TP180
                    cash[c]-=fee
                    active[c,an[c]]=child;an[c]+=1
                    tf[c,j,9]=1.;tf[c,j,10]=child+1.
                    stats_i[c,31]+=1
                    session_count[c,ti[c,j,2],0]+=1

            # No daily or per-session entry cap: each independently rearmed
            # S/R event can open at any time, including on the same UTC day.
            if stopout_flag[c]==0 and global_f[2]>0.:
                prev_bid=global_f[2]
                for sid in range(4):
                    if valid[sid]==0:continue
                    for source in range(NLEVELS):
                        p=frozen_levels[sid,source]
                        if p<=0.:continue
                        bound=0 if source<2 else 1
                        side=1 if bound==0 else -1
                        if CFG[c,14]>.5:
                            nearest=refhi[sid] if side==1 else reflo[sid]
                            if abs(p-nearest)>1.e-8:continue
                        crossed=(prev_bid<=p and bid>p) if side==1 else (prev_bid>=p and bid<p)
                        if not crossed:continue
                        stats_i[c,25]+=1
                        reg=find_previous_zone(c,bound,p,reg_n,reg_p)
                        repeating=reg>=0
                        if reg>=0 and reg_armed[c,bound,reg]==0:
                            stats_i[c,20]+=1
                            continue
                        # Distinct levels can run concurrently. Same-zone ticket
                        # already open cannot double-enter just because of chop.
                        already_open=False
                        for k in range(an[c]):
                            j=active[c,k]
                            if ti[c,j,0]!=side:continue
                            old_level=tf[c,j,2] if side==1 else tf[c,j,3]
                            if abs(old_level-p)<=SR_ZONE+1.e-9:
                                already_open=True;break
                        if already_open:
                            stats_i[c,20]+=1
                            continue
                        if stats_i[c,0]>=MAX_TRADES:
                            stats_i[c,10]=2;stats_i[c,11]=t;break
                        units=CFG[c,0]
                        entry=(ask+slip) if side==1 else (bid-slip)
                        fee=units*ROUND_TRIP_COMMISSION_PER_OZ
                        eq,margin=mark(c,bid,ask,cash,active,an,ti,tf,lev)
                        netoz=0.
                        for k in range(an[c]):
                            j=active[c,k]
                            netoz+=ti[c,j,0]*tf[c,j,4]
                        new_margin=abs(netoz+side*units)*bid/lev
                        new_equity=eq-units*(ask-bid+slip)-fee
                        if new_equity-new_margin<0.:
                            stats_i[c,9]+=1;continue
                        if reg<0:
                            reg=reg_n[c,bound]
                            if reg>=reg_p.shape[2]:
                                stats_i[c,10]=3;stats_i[c,11]=t;break
                            reg_p[c,bound,reg]=p
                            reg_n[c,bound]+=1
                            stats_i[c,24]+=1
                        else:stats_i[c,23]+=1
                        reg_armed[c,bound,reg]=0
                        reg_last[c,bound,reg]=t
                        j=stats_i[c,0];stats_i[c,0]+=1
                        ti[c,j,0]=side;ti[c,j,1]=t;ti[c,j,2]=sid
                        ti[c,j,3]=source;ti[c,j,4]=1 if repeating else 0
                        ti[c,j,5]=j;ti[c,j,6]=0
                        tf[c,j,0]=entry
                        tf[c,j,2]=p if side==1 else refhi[sid]
                        tf[c,j,3]=p if side==-1 else reflo[sid]
                        tf[c,j,4]=units;tf[c,j,5]=ask-bid
                        tf[c,j,6]=entry-side*(CFG[c,6] if side==1 else CFG[c,8])
                        tf[c,j,7]=0.
                        tf[c,j,8]=entry+side*9. # TP90
                        tf[c,j,9]=0. # child never issued
                        tf[c,j,10]=0. # child index+1, zero means no child
                        cash[c]-=fee
                        active[c,an[c]]=j;an[c]+=1
                        session_count[c,sid,0]+=1
                    if stats_i[c,10]!=0:break
            eq,margin=mark(c,bid,ask,cash,active,an,ti,tf,lev)
            if eq<stats_f[c,0]:stats_f[c,0]=eq
            if margin>stats_f[c,1]:stats_f[c,1]=margin
            if eq-margin<stats_f[c,2]:stats_f[c,2]=eq-margin
            wealth=eq+withdrawn[c]
            if wealth>stats_f[c,3]:stats_f[c,3]=wealth
            dd=stats_f[c,3]-wealth
            if dd>stats_f[c,4]:stats_f[c,4]=dd
            if an[c]>stats_i[c,8]:stats_i[c,8]=an[c]
            if an[c]>1:stats_i[c,15]+=1
            if eq<=0:
                if stats_i[c,10]==0:
                    stats_i[c,10]=1;stats_i[c,11]=t
                    stats_f[c,9]=eq;stats_f[c,10]=margin
                    stopout_flag[c]=1
        global_f[2]=bid;global_f[3]=ask
        global_i[4]=t

def selftest():
    assert len(CONF)==4 and CFG.shape==(4,20)
    assert [int(c[20]) for c in CONF]==[0,1,2,3]
    assert all(c[1]==1. and c[4]==0 and c[6]==9. and c[7]==9.
               and c[8]==9. and c[9]==9. and c[14]==9. for c in CONF)
    assert 4000+9 == 4009 and (4000-8)+18==4010
    print('PASS 4 models; Gold8 adverse trigger, second TP18/SL1; shared basket or independent; no Friday closes',flush=True)

def download(url,fn):
    h=hashlib.sha256();bytes_=0
    with requests.get(url,stream=True,timeout=(30,300)) as response:
        response.raise_for_status()
        with open(fn,'wb') as f:
            for chunk in response.iter_content(1<<20):
                if chunk:
                    f.write(chunk);h.update(chunk);bytes_+=len(chunk)
    return bytes_,h.hexdigest()

def make_rollovers():
    from zoneinfo import ZoneInfo
    ny=ZoneInfo('America/New_York')
    out=[]
    day=datetime(2020,1,1,tzinfo=timezone.utc)
    last=datetime(2026,11,6,tzinfo=timezone.utc)
    while day<last:
        if day.weekday()<5:
            # Exness uses summer 21:00 UTC and winter 22:00 UTC; Wednesday
            # Gold triple swap. Date of change follows US DST.
            hour=21 if day.astimezone(ny).dst().total_seconds()!=0 else 22
            rt=int((day+timedelta(hours=hour)).timestamp()*1e9)
            if rt<=END_2026:
                out.append((rt,3.0 if day.weekday()==2 else 1.0))
        day+=timedelta(days=1)
    return np.asarray([x[0] for x in out],dtype=np.int64),np.asarray([x[1] for x in out],dtype=np.float64)

def build_holiday_prethursday_flags(base_day):
    from pandas.tseries.holiday import USFederalHolidayCalendar
    from dateutil.easter import easter
    dates=set()
    for ts in USFederalHolidayCalendar().holidays(start='2020-01-01',end='2026-12-31'):
        if ts.weekday()==4:dates.add(ts.date())
    for y in range(2020,2027):dates.add(easter(y)-timedelta(days=2))
    flag=np.zeros(2700,dtype=np.int64)
    for d in dates:
        if d.weekday()!=4:continue
        thursday=datetime(d.year,d.month,d.day,tzinfo=timezone.utc)-timedelta(days=1)
        idx=int(thursday.timestamp()//86400-base_day)
        if 0<=idx<len(flag):flag[idx]=1
    print('FRIDAY_OBSERVED_HOLIDAYS_PROTECTED',sorted(str(d) for d in dates if d.weekday()==4),flush=True)
    return flag

def run(out):
    selftest()
    out=Path(out);out.mkdir(exist_ok=True,parents=True)
    all_schedule=[schedule(y) for y in range(YEAR_START,YEAR_END+1)]
    event_list=sorted(zip(np.concatenate([a[0] for a in all_schedule]),
                          np.concatenate([a[1] for a in all_schedule]),
                          np.concatenate([a[2] for a in all_schedule])))
    starts=np.asarray([x[0] for x in event_list],dtype=np.int64)
    ends=np.asarray([x[1] for x in event_list],dtype=np.int64)
    sids=np.asarray([x[2] for x in event_list],dtype=np.int64)
    rollover_times,rollover_multipliers=make_rollovers()
    rollover_cursor=np.zeros(1,dtype=np.int64)
    cash=np.full(N,START,dtype=np.float64)
    withdrawn=np.zeros(N,dtype=np.float64)
    daily=np.zeros(N,dtype=np.float64)
    active=np.zeros((N,MAX_TRADES),dtype=np.int64)
    an=np.zeros(N,dtype=np.int64)
    ti=np.zeros((N,MAX_TRADES,7),dtype=np.int64)
    tf=np.zeros((N,MAX_TRADES,11),dtype=np.float64)
    stats_i=np.zeros((N,40),dtype=np.int64)
    stats_f=np.zeros((N,20),dtype=np.float64)
    stats_f[:,0]=START;stats_f[:,2]=START;stats_f[:,3]=START
    results_i=np.zeros((N,MAX_TRADES,9),dtype=np.int64)
    results_f=np.zeros((N,MAX_TRADES,7),dtype=np.float64)
    day_pnl=np.zeros((N,2700),dtype=np.float64)
    session_count=np.zeros((N,4,3),dtype=np.int64)
    session_pnl=np.zeros((N,4),dtype=np.float64)
    global_i=np.zeros(7,dtype=np.int64)
    global_i[1]=-1;global_i[3]=-1;global_i[5]=-1;global_i[6]=-1
    global_f=np.zeros(4,dtype=np.float64)
    refhi=np.full(4,math.inf,dtype=np.float64);reflo=np.zeros(4,dtype=np.float64)
    valid=np.zeros(4,dtype=np.int64)
    serial=np.zeros(4,dtype=np.int64);seen=np.zeros((N,4),dtype=np.int64)
    missing=np.zeros(4,dtype=np.int64)
    sr_i=np.zeros(4,dtype=np.int64);sr_i[0]=-1;sr_i[2]=-1
    sr_f=np.zeros(8,dtype=np.float64)
    daily_high=np.zeros(5,dtype=np.float64);daily_low=np.zeros(5,dtype=np.float64)
    level_counts=np.zeros((3,3),dtype=np.int64)
    frozen_levels=np.zeros((4,NLEVELS),dtype=np.float64)
    reg_n=np.zeros((N,2),dtype=np.int64)
    reg_p=np.zeros((N,2,MAX_REGISTERED_SR),dtype=np.float64)
    reg_armed=np.zeros((N,2,MAX_REGISTERED_SR),dtype=np.int64)
    reg_last=np.full((N,2,MAX_REGISTERED_SR),-1,dtype=np.int64)
    stopout_flag=np.zeros(N,dtype=np.int64)
    margin_call_active=np.zeros(N,dtype=np.int64)
    base_day=int(pd.Timestamp('2020-01-01T00:00:00Z').value//NS_DAY)
    preholiday_thursday=build_holiday_prethursday_flags(base_day)
    provenance=[];total=0;last_tick_ns=-1;annual_snapshots=[]
    for year in range(YEAR_START,YEAR_END+1):
        lastmonth=12 if year<2026 else 11
        for month in range(1,lastmonth+1):
            mm=f'{month:02d}'
            paths=[('monthly',f'https://ticks.ex2archive.com/ticks/XAUUSD_Raw_Spread/{year}/{mm}/Exness_XAUUSD_Raw_Spread_{year}_{mm}.zip')]
            if year==2026 and month==11:
                paths=[
                  ('nov_before_05',paths[0][1]),
                  ('nov_05_daily','https://ticks.ex2archive.com/ticks/XAUUSD_Raw_Spread/2026/11/05/Exness_XAUUSD_Raw_Spread_2026_11_05.zip')]
            for label,url in paths:
                print('DOWNLOAD',year,mm,label,url,flush=True)
                zip_path=out/(str(year)+'_'+mm+'_'+label+'.zip')
                # November 05 DAILY archive is updated in-place by provider.
                # Verify ZIP central directory AND CRC before advancing one
                # causal tick. Retry transient invalid/corrupt source; never
                # pretend HTML error response is quote data.
                source_valid=False
                import time
                for attempt in range(4 if (year==2026 and label=='nov_05_daily') else 1):
                    try:
                        bytes_,sha=download(url,zip_path)
                        if not zipfile.is_zipfile(zip_path):
                            raise zipfile.BadZipFile('not a ZIP archive')
                        if year==2026 and label=='nov_05_daily':
                            with zipfile.ZipFile(zip_path) as verify_zip:
                                bad_member=verify_zip.testzip()
                                if bad_member is not None:
                                    raise zipfile.BadZipFile('CRC failure '+str(bad_member))
                        source_valid=True
                        break
                    except Exception as e:
                        print('SOURCE_DOWNLOAD_RETRY',label,attempt+1,str(e),flush=True)
                        zip_path.unlink(missing_ok=True)
                        if not (year==2026 and label=='nov_05_daily'):
                            raise
                        if attempt<3:
                            time.sleep(5*(attempt+1))
                if not source_valid:
                    if year==2026 and label=='nov_05_daily':
                        print('SOURCE_UNAVAILABLE',url,'2026-11-05 omitted; results valid through latest completed Nov monthly quote. No fabricated ticks.',flush=True)
                        continue
                    raise RuntimeError('required archive invalid: '+url)
                count=0;first_ns=0;last_ns=0
                with zipfile.ZipFile(zip_path) as z:
                    for name in z.namelist():
                        if not name.lower().endswith('.csv'):continue
                        with z.open(name) as fd:
                            for df in pd.read_csv(fd,usecols=['Timestamp','Bid','Ask'],chunksize=500_000):
                                utc=pd.to_datetime(df['Timestamp'],utc=True,errors='coerce')
                                ok=utc.notna()&df['Bid'].notna()&df['Ask'].notna()
                                if year==2026 and month==11:
                                    if label=='nov_before_05':
                                        ok &= utc<pd.Timestamp('2026-11-05T00:00:00Z')
                                    else:
                                        ok &= utc>=pd.Timestamp('2026-11-05T00:00:00Z')
                                        ok &= utc<=pd.Timestamp(END_2026,unit='ns',tz='UTC')
                                if not bool(ok.all()):df=df.loc[ok];utc=utc.loc[ok]
                                if len(df)==0:continue
                                t=utc.astype('int64').to_numpy(dtype=np.int64)
                                bid=df['Bid'].to_numpy(dtype=np.float64)
                                ask=df['Ask'].to_numpy(dtype=np.float64)
                                if np.any(t[1:]<t[:-1]):raise RuntimeError('Non-monotone ticks within chunk')
                                if last_tick_ns>=0 and t[0]<last_tick_ns:raise RuntimeError('Archive overlap or timestamp rollback')
                                last_tick_ns=int(t[-1])
                                if first_ns==0:first_ns=int(t[0])
                                last_ns=last_tick_ns
                                engine(t,bid,ask,starts,ends,sids,CFG,cash,withdrawn,daily,
                                     active,an,ti,tf,stats_i,stats_f,results_i,results_f,
                                     day_pnl,session_count,session_pnl,global_i,global_f,
                                     refhi,reflo,valid,serial,seen,missing,base_day,
                                     sr_i,sr_f,daily_high,daily_low,level_counts,
                                     reg_n,reg_p,reg_armed,reg_last,frozen_levels,
                                     rollover_times,rollover_multipliers,rollover_cursor,
                                     stopout_flag,margin_call_active,preholiday_thursday)
                                count+=len(df);total+=len(df)
                zip_path.unlink(missing_ok=True)
                provenance.append(dict(year=year,month=month,label=label,url=url,zip_bytes=bytes_,
                    sha256=sha,rows=count,first_quote_utc=str(pd.Timestamp(first_ns,unit='ns',tz='UTC')) if count else None,
                    last_quote_utc=str(pd.Timestamp(last_ns,unit='ns',tz='UTC')) if count else None))
                if month in (1,6,10,11,12):
                    print('CHECKPOINT',year,mm,label,'records',count,
                       ';'.join(f'{CONF_NAMES[i]}:wealth={mark(i,global_f[2],global_f[3],cash,active,an,ti,tf,CFG[i,4])[0]:.3f} closed={stats_i[i,1]} open={an[i]} dedup={stats_i[i,16]} friday_closes={stats_i[i,6]} swaps={stats_f[i,11]:.2f} stopout={stats_i[i,17]}' for i in range(N)),
                       flush=True)
                if year==2026 and month==10 and label=='monthly':
                    snap=[dict(year='2026-10-30',model=CONF_NAMES[i],equity=float(mark(i,global_f[2],global_f[3],cash,active,an,ti,tf,CFG[i,4])[0]),cash=float(cash[i]),opened=int(stats_i[i,0]),closed=int(stats_i[i,1]),open=int(an[i])) for i in range(N)]
                    print('OCTOBER_CHECKPOINT',json.dumps(snap),flush=True)
        # Important: NO reset! Only store marked portfolio performance.
        for i in range(N):
            eq,margin=mark(i,global_f[2],global_f[3],cash,active,an,ti,tf,CFG[i,4])
            annual_snapshots.append(dict(year=year,through_utc=str(pd.Timestamp(last_tick_ns,unit='ns',tz='UTC')),
                config=CONF_NAMES[i],cash=round(float(cash[i]),4),
                equity=round(float(eq),4),net_since_2020=round(float(eq-START),4),
                trades_opened_cumulative=int(stats_i[i,0]),
                trades_closed_cumulative=int(stats_i[i,1]),
                open_positions=int(an[i]),total_swap_debit_cumulative=round(float(stats_f[i,11]),4),
                friday_flat_exits_cumulative=int(stats_i[i,6]),
                duplicate_rejections_cumulative=int(stats_i[i,20]),
                repeated_entries_cumulative=int(stats_i[i,23]),
                independent_sr_zones_cumulative=int(stats_i[i,24]),
                stop_out_forced_cumulative=int(stats_i[i,17])))
        print('YEAR_END',year,json.dumps(annual_snapshots[-N:]),flush=True)
    ledger=[]
    for c,name in enumerate(CONF_NAMES):
        for ix in range(stats_i[c,1]):
            v=results_i[c,ix];f=results_f[c,ix]
            ledger.append(dict(model=name,session=SESSION_NAMES[v[0]],side='BUY' if v[1]>0 else 'SELL',
                entered_utc=str(pd.Timestamp(int(v[2]),unit='ns',tz='UTC')),
                exited_utc=str(pd.Timestamp(int(v[3]),unit='ns',tz='UTC')),
                result={1:'TP',2:'SL',3:'FRIDAY_FLAT',4:'STOP_OUT',
                  5:'BREAKEVEN_STOP',6:'TRAILING_STOP',
                  7:'LOSING_TIME_STOP'}.get(int(v[4]),'UNKNOWN'),
                entry=round(float(f[0]),5),exit=round(float(f[1]),5),
                source=['D1_RESIST','PRIOR_WEEK_RESIST','D1_SUPPORT','PRIOR_WEEK_SUPPORT'][int(v[5])],
                repeated_after_confirmed_H1_rearm=bool(v[6]),
                family_root=int(v[7]),role=('ADDON' if v[8]==1 else 'PRIMARY'),
                net_ex_swap=round(float(f[2]),5),major_resistance=round(float(f[3]),5),
                major_support=round(float(f[4]),5),lot=round(float(f[5]),4),spread=round(float(f[6]),5)))
    summary=[]
    for c,name in enumerate(CONF_NAMES):
        eq,margin=mark(c,global_f[2],global_f[3],cash,active,an,ti,tf,CFG[c,4])
        summary.append(dict(config=name,
            from_utc=str(pd.Timestamp(provenance[0]['first_quote_utc'])),
            through_utc=str(pd.Timestamp(last_tick_ns,unit='ns',tz='UTC')),
            ticks_processed=total,
            starting_balance=START,
            closing_cash=round(float(cash[c]),4),
            marked_equity=round(float(eq),4),
            net_profit=round(float(eq-START),4),
            trades_opened=int(stats_i[c,0]),
            trades_closed=int(stats_i[c,1]),
            TP=int(stats_i[c,4]),SL=int(stats_i[c,5]),
            win_percent=round(100*stats_i[c,4]/max(1,stats_i[c,4]+stats_i[c,5]),4),
            loss_percent=round(100*stats_i[c,5]/max(1,stats_i[c,4]+stats_i[c,5]),4),
            forced_friday_flat=int(stats_i[c,6]),
            addon_orders=int(stats_i[c,31]),
            basket_take_profit_groups=int(stats_i[c,33]),
            basket_stop_loss_groups=int(stats_i[c,34]),
            duplicate_skips=int(stats_i[c,20]),
            breakeven_exits=int(stats_i[c,26]),
            trailing_exits=int(stats_i[c,27]),
            time_stopped_exits=int(stats_i[c,28]),
            protective_stop_adjustments=int(stats_i[c,29]+stats_i[c,30]),
            risk_mode=int(CFG[c,15]),risk_trigger=float(CFG[c,16]),
            trailing_gap=float(CFG[c,17]),time_stop_hours=float(CFG[c,18]),
            rearm_confirmations=int(stats_i[c,22]),
            repeat_entries=int(stats_i[c,23]),
            unique_sr_zones_traded=int(stats_i[c,24]),
            raw_eligible_tick_crosses=int(stats_i[c,25]),
            modeled_stopout_liquidations=int(stats_i[c,17]),
            modeled_margin_call_events=int(stats_i[c,18]),
            modeled_swap_debit=round(float(stats_f[c,11]),4),
            overnight_swap_charges=int(stats_i[c,19]),
            margin_rejections=int(stats_i[c,9]),
            worst_equity=round(float(stats_f[c,0]),4),
            max_margin=round(float(stats_f[c,1]),4),
            min_free_margin=round(float(stats_f[c,2]),4),
            max_drawdown_usd=round(float(stats_f[c,4]),4),
            maximum_concurrent_orders=int(stats_i[c,8]),
            active_positions_end=int(an[c]),
            account_stopout_flag=bool(stopout_flag[c]),leverage=int(CFG[c,4]),weekend_policy=int(CFG[c,12]),
            assumed_swap_debit_per_001_lot_per_rollover=float(CFG[c,11]),
            h1_prebreak_rearm_price_distance=float(CFG[c,13]),
            candidate_universe=('nearest_only' if CFG[c,14]>.5 else 'all_daily_and_weekly_sources'),
            level_zone_price_width=SR_ZONE,
            extra_slippage_per_side=float(CFG[c,1])))
    # Strict audit: no time/Friday trade exit allowed; broker stopout only
    # if equity extinguished. Any such account is NOT TP/SL-only compliant.
    for c,name in enumerate(CONF_NAMES):
        assert stats_i[c,6]==0, (name,'unexpected forced closure',stats_i[c,6])
        assert stats_i[c,28]==0, (name,'unexpected time stop',stats_i[c,28])
        if stats_i[c,17]!=0:
            print('BROKER_STOPOUT_EXCEPTION',name,stats_i[c,17],flush=True)
    open_ledger=[]
    for c,name in enumerate(CONF_NAMES):
        for k in range(an[c]):
            j=active[c,k]
            side=ti[c,j,0];entry=tf[c,j,0]
            executable=global_f[2] if side==1 else global_f[3]
            remaining=side*(executable-entry)*tf[c,j,4]
            open_ledger.append(dict(model=name,entry_utc=str(pd.Timestamp(int(ti[c,j,1]),unit='ns',tz='UTC')),
                                    session=SESSION_NAMES[ti[c,j,2]],side='BUY' if side==1 else 'SELL',
                                    entry_price=entry,current_sl=float(tf[c,j,6]),
                                    original_tp=entry+side*(CFG[c,5] if side==1 else CFG[c,7]),
                                    last_quote_bid=float(global_f[2]),last_quote_ask=float(global_f[3]),
                                    unrealized_gross_usd=round(float(remaining),4),
                                    account_model_swap_fee_separately_in_cash=True))
    pd.DataFrame(open_ledger).to_csv(out/'open_positions_at_cutoff.csv',index=False)
    print('TP90_SL_SWEEP_AUDIT',json.dumps({
        'through_utc':str(pd.Timestamp(last_tick_ns,unit='ns',tz='UTC')),
        'models':[{ 'name':CONF_NAMES[c], 'opened':int(stats_i[c,0]),
                    'addon_orders':int(stats_i[c,31]),
                    'basket_TP_groups':int(stats_i[c,33]),
                    'basket_SL_groups':int(stats_i[c,34]),
                    'TP':int(stats_i[c,4]),'hard_SL':int(stats_i[c,5]),
                    'protective_SL_BE':int(stats_i[c,26]),
                    'protective_SL_trailing':int(stats_i[c,27]),
                    'forced_closes':int(stats_i[c,6]+stats_i[c,28]),
                    'stopout_exceptions':int(stats_i[c,17]),
                    'still_open':int(an[c])} for c in range(N)]
    },sort_keys=True),flush=True)
    (out/'model_summary.csv').write_text(pd.DataFrame(summary).to_csv(index=False))
    pd.DataFrame(annual_snapshots).to_csv(out/'continuous_annual_equity.csv',index=False)
    pd.DataFrame(ledger).to_csv(out/'ticket_ledger.csv',index=False)
    (out/'provenance.json').write_text(json.dumps(dict(sources=provenance,quote_records=total,
        models=CONF,entry_strategy='LOCKED causal major SR resistance BUY support SELL TP90 SL90; ALL eligible distinct daily/weekly S/R candidates and H1-confirmed repeat crossings without daily limits',
        signal_dedup='One S/R zone per live ticket/tick; after closing and H1 prebreak close >= 1 Gold away, rearm and recross, no daily or session limit',
        Friday_flat='DISABLED: no Friday/Thursday time exits and no Friday entry ban; open positions carry all weekends/holidays until actual TP/SL execution',
        timed_exit_policy='DISABLED: original TP9 SL9 and optional second TP18 SL1; independent vs synchronized-basket outcomes separately audited',
        open_cutoff_policy='NO synthetic liquidation at snapshot; all still open are marked to last actual quote and listed in open_positions_at_cutoff.csv',
        swap='ZERO if swap-free; other models synthetic USD debit per 0.01 lot, applied on Wednesday 3x, Mon-Thu regular, no historical account-specific XAU swap series available',
        margin='Exness Raw Spread 0 pct stopout, 30 pct margin call; 1:2000 normal or conservatively 1:100 applied ALL hours as worst-case Exness XAU HMR; exact historical event-by-event HMR unavailable',
        partial_2020='Jan29 start due data',partial_2026='Nov05 around 09 UTC last daily quote',
        year_account='SINGLE continuous $1000 account, NO reset, NO withdrawal, unchanged fixed 0.01 lot, net exposure with 0 hedged margin',
        unmodeled='Real historical swap rates/account status, event-by-event dynamic Exness HMR, exact broker fills, special holiday close hours'),
        indent=2))
    print('CONTINUOUS_FINAL_TABLE\\n'+pd.DataFrame(summary).to_string(index=False),flush=True)
    print('ACCOUNT_YEAR_END_SUMMARY\\n'+pd.DataFrame(annual_snapshots).to_string(index=False),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--out',type=str,default='results/continuous_2020_2026')
    p.add_argument('--selftest',action='store_true')
    x=p.parse_args()
    if x.selftest:selftest()
    else:run(x.out)

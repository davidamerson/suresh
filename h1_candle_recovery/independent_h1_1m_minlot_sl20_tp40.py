"""Independent per-hour counterfactual group study: Exness XAUUSD Raw Spread.

Every eligible UTC H1 04:00..19:00 first quote starts a FRESH, INDEPENDENT
group with $1,000,000 initial capital, regardless of whether any other
hypothetical group's path would still be running. The group simulations can
overlap in time but DO NOT share an account, margin, PnL, compounding or
positions; do not interpret sum(PnL) as tradable one-account returns.

Signal: previous COMPLETED H1 BID candle Close>Open BUY; Close<Open SELL;
exactly first raw tick of new H1 (late >10min or spread>=stop skipped).
Each recovery group one active ticket, TP at +10 * user diagram pip ($1.00
gold per ounce), SL at -5 diagram pips ($0.50 gold per ounce).
After each SL place opposite order immediately at the same quote, including
when spread is wider than the stop; this is a literal mechanical replay.
Dynamic minimum break-even lot on EACH recovery step, rounded UP in 0.01 lots:
required_lot = max(0.01, ceil((START - realized_group_balance) / 0.93)*0.01).
The exact $3.93 per 0.01 lot is TP gross $1.00 minus $0.07 Raw Spread
commission at nominal 10 diagram pip (+$1.00 per ounce) TP. Price gaps may
alter SL losses, which are included in realized_group_balance. TP first
hit ends group,
NO calendar/time/basket-based force exit. Per-group initial balance $1,000,000.

True Ask BUY entry/Bid BUY exit, Bid SELL entry/Ask SELL exit, tick gaps
included, $7 per lot roundtrip assumed Exness Raw Spread commission.
Compare one analytical no-margin variant, 1:2000 margin and XAUUSD-specific 200-lot cap both daytime and nighttime, and 1:200 all-hour stress. No swap, live latency,
actual varying broker HMR calendar, broker negative balance protection.
Use of same public H1 candle reference as previous confirmed backtests.
"""
import argparse
import hashlib
import json
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from numba import njit

START = 1000000.0
TP = 4.0
SL = 2.0
BASELOT = 0.01
LOT_STEP = 0.01
COMMISSION_PER_LOT = 7.0
NOMINAL_TP_NET_PER_LOT = TP*100.0-COMMISSION_PER_LOT  # TP per 100 oz minus $7 commission per lot
N = 3
MAXG = 40000
MAXO = 400000
MODELS = ("INDEPENDENT_IDEAL_NO_MARGIN","INDEPENDENT_EXNESS_1_2000","INDEPENDENT_HMR_STRESS_1_200")

# Group float fields
BAL=0;LOT=1;ENT=2;PEAK=3;MINEQ=4;MAXDD=5;MAXLOT=6
REQLOT=7;REQMARGIN=8;REQEQ=9;MARKEQ=10;FEES=11
# Group integer fields
STATUS=0;SIDE=1;STAGE=2;CURORDER=3;NORD=4;FIRSTSIDE=5;FAIL=6
# status: 1=open ticket, 2=TP complete, 3=broker unable to open mandatory
# order, 4=equity stopout, 5=pending mandatory reversal (wide spread)
# failure: 1=insufficient margin, 2=assumed max-order-size cap,
# 3=insufficient equity to open, 4=ticket ledger capacity
# Group timestamps
STARTNS=0;ENDNS=1
# Ticket float fields
OLOT=0;OENTRY=1;OEXIT=2;OFEE=3;ONET=4;OMARGIN=5;OSPREAD=6
# Ticket int fields
OGROUP=0;OSTAGE=1;OSIDE=2;OEXITREASON=3;OENTRYNS=4;OEXITNS=5
# reason: 0 open, 1 take profit, 2 stop loss, 3 equity stopout

def state():
    return dict(
        gf=np.zeros((N,MAXG,12),np.float64),
        gi=np.zeros((N,MAXG,7),np.int64),
        gt=np.zeros((N,MAXG,2),np.int64),
        tf=np.zeros((N,MAXO,7),np.float64),
        ti=np.zeros((N,MAXO,6),np.int64),
        ng=np.zeros(N,np.int64),
        no=np.zeros(N,np.int64),
        na=np.zeros(N,np.int64),
        active=np.zeros((N,MAXG),np.int64),
        rejected_late=np.zeros(N,np.int64),
        rejected_spread=np.zeros(N,np.int64),
        valid_ticks=np.zeros(1,np.int64),
        prev_hour=np.array([-1],np.int64),
        prev_tick=np.zeros(1,np.int64),
        last_bid_ask=np.zeros(2,np.float64)
    )

@njit
def enter_order(q,g,newside,ns,bid,ask,gf,gi,tf,ti,no):
    """Opens next mandatory order or sets terminal block reason."""
    stage=int(gi[q,g,STAGE])
    # No martingale/doubling. Select the *smallest* broker-volume-step
    # lot for which the group's realized balance, after nominal TP and
    # the new trade's commission, is >= its independent initial $1M.
    # All previous SL gap losses and opening fees are already in BAL.
    deficit=START-gf[q,g,BAL]
    units=1
    if deficit>0.0:
        units=max(1,int(np.ceil((deficit-1e-8)/(NOMINAL_TP_NET_PER_LOT*LOT_STEP))))
    v=LOT_STEP*units
    # If the lot is too large, broker 200-lot size cap/margin stops group.

    ep=ask if newside==1 else bid
    fee=COMMISSION_PER_LOT*v
    spread=ask-bid
    initial_equity=gf[q,g,BAL]-fee-spread*100.0*v
    lev=0.0 if q==0 else (2000.0 if q==1 else 200.0)
    margin=0.0 if lev==0.0 else ep*100.0*v/lev
    h=(ns//3600000000000)%24
    maxlot=200.0  # XAUUSD is a NIGHTTIME 200-lot exception in Exness instrument-specific FAQ
    fail=0
    if initial_equity<=0.0:
        fail=3
    elif lev>0.0 and v>maxlot+1e-9:
        fail=2
    elif lev>0.0 and initial_equity<margin:
        fail=1
    if fail:
        gi[q,g,STATUS]=3
        gi[q,g,FAIL]=fail
        gf[q,g,REQLOT]=v
        gf[q,g,REQMARGIN]=margin
        gf[q,g,REQEQ]=initial_equity
        return False
    k=int(no[q])
    if k>=MAXO:
        raise ValueError("MAXO exhausted: increase ticket ledger")
    no[q]+=1
    gf[q,g,BAL]-=fee
    gf[q,g,FEES]+=fee
    gf[q,g,LOT]=v
    gf[q,g,ENT]=ep
    if v>gf[q,g,MAXLOT]:
        gf[q,g,MAXLOT]=v
    gi[q,g,SIDE]=newside
    gi[q,g,STATUS]=1
    gi[q,g,CURORDER]=k
    gi[q,g,NORD]+=1
    tf[q,k,OLOT]=v
    tf[q,k,OENTRY]=ep
    tf[q,k,OFEE]=fee
    tf[q,k,OMARGIN]=margin
    tf[q,k,OSPREAD]=spread
    ti[q,k,OGROUP]=g
    ti[q,k,OSTAGE]=stage+1
    ti[q,k,OSIDE]=newside
    ti[q,k,OENTRYNS]=ns
    return True

@njit
def mark(q,g,bid,ask,gf,gi):
    eq=gf[q,g,BAL]
    if gi[q,g,STATUS]==1:
        x=bid if gi[q,g,SIDE]==1 else ask
        eq+=gi[q,g,SIDE]*(x-gf[q,g,ENT])*100.0*gf[q,g,LOT]
    gf[q,g,MARKEQ]=eq
    if eq>gf[q,g,PEAK]:
        gf[q,g,PEAK]=eq
    if eq<gf[q,g,MINEQ]:
        gf[q,g,MINEQ]=eq
    dd=gf[q,g,PEAK]-eq
    if dd>gf[q,g,MAXDD]:
        gf[q,g,MAXDD]=dd

@njit
def process_group_same_tick(q,g,now,bid,ask,gf,gi,gt,tf,ti,no):
    """Execute every mandatory reverse on the exact stop-hit quote.
    A position can be *immediately* SL at opening if spread >= SL distance.
    This is a mechanical price-path counterfactual, not a claim that an
    Exness broker accepts attached SL inside its spread."""
    for rep in range(40):
        if gi[q,g,STATUS]!=1:
            raise ValueError("Unexpected state in active group")
        side=int(gi[q,g,SIDE])
        px=bid if side==1 else ask
        movement=side*(px-gf[q,g,ENT])
        gross=movement*100.0*gf[q,g,LOT]
        eq=gf[q,g,BAL]+gross
        stopped=eq<=0.0
        take=movement>=TP-1e-9
        loss=movement<=-SL+1e-9
        if not (stopped or take or loss):
            mark(q,g,bid,ask,gf,gi)
            return False
        k=int(gi[q,g,CURORDER])
        ti[q,k,OEXITNS]=now
        tf[q,k,OEXIT]=px
        reason=3 if stopped else (1 if take else 2)
        ti[q,k,OEXITREASON]=reason
        tf[q,k,ONET]=gross-tf[q,k,OFEE]
        gf[q,g,BAL]+=gross
        if stopped:
            gi[q,g,STATUS]=4
            gt[q,g,ENDNS]=now
            mark(q,g,bid,ask,gf,gi)
            return True
        if take:
            gi[q,g,STATUS]=2
            gt[q,g,ENDNS]=now
            mark(q,g,bid,ask,gf,gi)
            return True
        gi[q,g,STAGE]+=1
        # RULE: on EVERY SL, the next opposite ticket is mandatory, at once.
        # No invented spread filter and no pending/deferred reversal.
        if not enter_order(q,g,-side,now,bid,ask,gf,gi,tf,ti,no):
            gt[q,g,ENDNS]=now
            mark(q,g,bid,ask,gf,gi)
            return True
        # New liquidation quote at SAME tick may already touch the SL.
        # Keep processing until TP, next order blocked, or a live ticket
        # remains within the TP/SL range. No group-to-group money sharing.
    raise ValueError("Unbounded same-tick reversal chain; safeguard exceeded")

@njit
def chunk(ns,bids,asks,book,base,gf,gi,gt,tf,ti,ng,no,na,active,
          rejected_late,rejected_spread,valid_ticks,prev_hour,prev_tick,
          last_bid_ask):
    for i in range(len(ns)):
        now=ns[i]; bid=bids[i]; ask=asks[i]
        if not (np.isfinite(bid) and np.isfinite(ask) and ask>=bid>0):
            continue
        if prev_tick[0]!=0 and now<prev_tick[0]:
            raise ValueError("Unsorted Exness ticks")
        h=now//3600000000000
        new_hour=h!=prev_hour[0]

        # Every previous hourly entry starts its OWN separate virtual path.
        # Every existing group is advanced without money or margin sharing.
        for q in range(N):
            a=0
            while a<na[q]:
                g=int(active[q,a])
                done=process_group_same_tick(q,g,now,bid,ask,gf,gi,gt,tf,ti,no)
                if done:
                    na[q]-=1
                    active[q,a]=active[q,na[q]]
                else:
                    a+=1

        idx=h-base
        sign=0
        if new_hour and 0<=idx<len(book):
            sign=int(book[idx])
        if sign!=0:
            # The user requested EVERY eligible hour. Track spread/late
            # diagnostics but DO NOT SKIP the hourly group for either.
            late=(now//60000000000)%60>=10
            wide=(ask-bid)>=SL-1e-9
            for q in range(N):
                if late: rejected_late[q]+=1
                if wide: rejected_spread[q]+=1
                g=int(ng[q])
                if g>=MAXG:
                    raise ValueError("MAXG too small for all hourly entries")
                ng[q]+=1
                gt[q,g,STARTNS]=now
                gf[q,g,BAL]=START
                gf[q,g,MARKEQ]=START
                gf[q,g,PEAK]=START
                gf[q,g,MINEQ]=START
                gi[q,g,FIRSTSIDE]=sign
                gi[q,g,STAGE]=0
                if enter_order(q,g,sign,now,bid,ask,gf,gi,tf,ti,no):
                    # Trigger any immediate spread-induced SL on the same
                    # first raw tick rather than falsely treating as open.
                    done=process_group_same_tick(q,g,now,bid,ask,
                                                gf,gi,gt,tf,ti,no)
                    if not done:
                        active[q,na[q]]=g
                        na[q]+=1
                else:
                    gt[q,g,ENDNS]=now
                    mark(q,g,bid,ask,gf,gi)

        prev_hour[0]=h
        prev_tick[0]=now
        last_bid_ask[0]=bid;last_bid_ask[1]=ask
        valid_ticks[0]+=1

def process_batch(ns,bid,ask,base,book,s):
    chunk(ns,bid,ask,book,base,*[s[k] for k in
       ("gf","gi","gt","tf","ti","ng","no","na","active",
        "rejected_late","rejected_spread","valid_ticks",
        "prev_hour","prev_tick","last_bid_ask")])

def h1_book(csv):
    candles=pd.read_csv(csv)
    candles=candles[candles.complete.astype(str).str.lower().isin(("true","1"))]
    candles=candles.sort_values("hour_epoch").reset_index(drop=True)
    hrs=candles.hour_epoch.to_numpy(np.int64)
    op=candles.bid_open.to_numpy(float)
    cl=candles.bid_close.to_numpy(float)
    base=int(hrs[0])
    book=np.zeros(int(hrs[-1]-base+5),np.int8)
    eligible=0;doji=0
    for j in range(len(hrs)):
        target=hrs[j]+1
        if not (4<=target%24<=19):
            continue
        if not (np.isfinite(op[j]) and np.isfinite(cl[j])):
            continue
        if cl[j]==op[j]:
            doji+=1
            continue
        sign=1 if cl[j]>op[j] else -1
        book[target-base]=sign
        eligible+=1
    print("SCHEDULE",json.dumps(dict(
        completed_H1=len(candles),scheduled_eligible_directional_hours=eligible,
        buy_signal_count=int((book==1).sum()),
        sell_signal_count=int((book==-1).sum()),
        doji_excluded=doji,allowed_UTC_entry_hours="04:00 through 19:00",
        previous_candle_only=True)),flush=True)
    assert eligible>1000
    return base,book

def selftest():
    """Every rule is tested for this chosen TP/SL including BUY and SELL,
    actual cost rounded minimum lots, independent overlap, high spread,
    and the assumed 200-lot per-order cap."""
    start=1000
    unit=3600000000000
    sll=float(SL); tpp=float(TP)
    if not (abs(tpp-2*sll)<1e-12 and sll>0):
        raise AssertionError("The three chosen scenarios require 1:2 risk/reward")

    shapes=[
        [100.,100.+tpp],
        [100.,100.-sll,100.-sll-tpp],
        [100.,100.-sll,100.,100.+tpp],
        [100.,100.-sll,100.,100.-sll,100.-sll-tpp],
        [100.,100.-sll,100.,100.-sll,100.,100.+tpp],
    ]
    for shape,stages in zip(shapes,range(1,6)):
        # Independently compute the *exact* theoretical lot and group PnL,
        # never using the production enter_order sizing routine.
        theoretical=START
        expectedlots=[]
        for ix in range(stages):
            deficit=max(0.0,START-theoretical)
            lot=0.01*max(1,int(np.ceil((deficit-1e-8)/((TP*100.-7.)*.01))))
            expectedlots.append(lot)
            theoretical+= (tpp*100.-7.)*lot if ix==stages-1 else -(sll*100.+7.)*lot
        for sign in (1,-1):
            bk=np.zeros(6,np.int8);bk[1]=sign
            prices=np.asarray(shape if sign==1 else [200.-v for v in shape],np.float64)
            stamps=np.array([(start+1)*unit+i*1000000000
                             for i in range(len(prices))],np.int64)
            state0=state()
            process_batch(stamps,prices,prices,start,bk,state0)
            for q in range(N):
                assert int(state0["ng"][q])==1,(stages,sign,q,"wrong number of groups")
                assert int(state0["gi"][q,0,STATUS])==2,(stages,sign,q,"not TP")
                assert int(state0["gi"][q,0,NORD])==stages,(stages,sign,q,"bad stage count")
                actual=float(state0["gf"][q,0,BAL])
                assert abs(actual-theoretical)<1e-5,(stages,sign,q,actual,theoretical)
                assert int(state0["gi"][q,0,FIRSTSIDE])==sign
                for ix,expectedlot in enumerate(expectedlots):
                    actual_lot=float(state0["tf"][q,ix,OLOT])
                    assert abs(actual_lot-expectedlot)<1e-8,(
                        stages,sign,q,ix,actual_lot,expectedlot)
                assert actual>=START-1e-6,(stages,sign,q,"loss after TP")

    # The recovered fourth order must be .03 (not .04 doubling).
    assert len(expectedlots)==5 and abs(expectedlots[3]-.03)<1e-8,expectedlots
    bk=np.zeros(10,np.int8);bk[1]=1;bk[2]=-1;bk[3]=1
    times=np.array([(start+k)*unit for k in (1,2,3)],np.int64)
    prices=np.array([100.,100.+sll/10.,100.+sll/5.],np.float64)
    separate=state()
    process_batch(times,prices,prices,start,bk,separate)
    assert np.array_equal(separate["ng"],np.array([3,3,3]))
    assert np.array_equal(separate["na"],np.array([3,3,3]))
    for q in range(N):
        assert all(abs(separate["gf"][q,g,BAL]-(START-.07))<1e-6 for g in range(3))
        assert all(separate["gi"][q,g,NORD]==1 for g in range(3))

    # Even at 21:00 UTC an order <=200 lots should pass and >200 should fail.
    sn=state()
    night=21*unit
    sn["gf"][1,0,BAL]=START-163.84*NOMINAL_TP_NET_PER_LOT
    sn["gi"][1,0,STAGE]=16
    ok=enter_order(1,0,1,night,100.,100.,sn["gf"],sn["gi"],sn["tf"],sn["ti"],sn["no"])
    assert ok and abs(sn["gf"][1,0,LOT]-163.84)<1e-8,"163.84 lots must pass"
    sn["gf"][1,1,BAL]=START-327.68*NOMINAL_TP_NET_PER_LOT
    sn["gi"][1,1,STAGE]=17
    ok=enter_order(1,1,1,night,100.,100.,sn["gf"],sn["gi"],sn["tf"],sn["ti"],sn["no"])
    assert not ok and int(sn["gi"][1,1,FAIL])==2,"327.68 lots must block"

    # Literal all-hours rule: spread > SL still starts and reverses now.
    wide=state()
    hb=np.zeros(8,np.int8);hb[1]=1
    stamps=np.array([(start+1)*unit],np.int64)
    process_batch(stamps,np.array([100.]),np.array([100.+1.4*sll]),start,hb,wide)
    for q in range(N):
        assert int(wide["ng"][q])==1 and int(wide["rejected_spread"][q])==1
        assert int(wide["gi"][q,0,NORD])>=2,(q,"spread reversal missing")
        assert int(wide["gi"][q,0,STATUS]) in (3,4),(q,"cascade left live")
    late=state()
    stamps=np.array([(start+1)*unit+19*60000000000],np.int64)
    process_batch(stamps,np.array([100.]),np.array([100.]),start,hb,late)
    assert np.array_equal(late["ng"],np.array([1,1,1]))
    assert np.array_equal(late["rejected_late"],np.array([1,1,1]))
    print("SELFTEST_PASSED SL",SL,"TP",TP,
          "all 5 recovery paths BUY/SELL cost-correct minimum lots, separate hourly groups, XAUUSD cap and wide spread",flush=True)

def download(url,dst):
    sha=hashlib.sha256();size=0
    with requests.get(url,stream=True,timeout=(30,300)) as r:
        r.raise_for_status()
        with dst.open("wb") as w:
            for part in r.iter_content(1024*1024):
                if part:
                    w.write(part);sha.update(part);size+=len(part)
    if not zipfile.is_zipfile(dst):
        raise ValueError("Bad ZIP "+url)
    return sha.hexdigest(),size

def iso(n):
    return str(pd.Timestamp(int(n),unit="ns",tz="UTC")) if n else None

def write_audit(s,folder,first,last,provenance,book):
    gf=s["gf"];gi=s["gi"];gt=s["gt"];tf=s["tf"];ti=s["ti"]
    groups=[];orders=[]
    for q,name in enumerate(MODELS):
        for g in range(int(s["ng"][q])):
            status=int(gi[q,g,STATUS])
            bal=float(gf[q,g,BAL]);m=float(gf[q,g,MARKEQ])
            groups.append(dict(
                model=name,group_id=g+1,entry_utc=iso(gt[q,g,STARTNS]),
                final_event_utc=iso(gt[q,g,ENDNS]),
                entry_year=pd.Timestamp(gt[q,g,STARTNS],unit="ns",tz="UTC").year,
                first_direction="BUY" if gi[q,g,FIRSTSIDE]==1 else "SELL",
                outcome={1:"OPEN_AT_DATA_END",2:"TP_COMPLETED",3:"BROKER_BLOCKED",
                         4:"EQUITY_STOP_OUT",5:"MANDATORY_REVERSAL_PENDING"}.get(status,"UNKNOWN"),
                stages_executed=int(gi[q,g,NORD]),
                starting_capital_usd=START,
                terminal_balance_usd=bal,
                marked_equity_usd=m,
                realized_pnl_usd=bal-START,
                marked_pnl_usd=m-START,
                max_group_marked_drawdown_usd=float(gf[q,g,MAXDD]),
                min_group_marked_equity_usd=float(gf[q,g,MINEQ]),
                maximum_lot_used=float(gf[q,g,MAXLOT]),
                total_commission_usd=float(gf[q,g,FEES]),
                required_next_lot_if_blocked=float(gf[q,g,REQLOT]),
                margin_required_for_next_lot=float(gf[q,g,REQMARGIN]),
                would_be_equity_after_new_spread_and_fee=float(gf[q,g,REQEQ]),
                block_reason={1:"MARGIN",2:"MAX_LOT",3:"INSUFFICIENT_EQUITY"}.get(
                    int(gi[q,g,FAIL]),"")))
        for k in range(int(s["no"][q])):
            groupno=int(ti[q,k,OGROUP])
            finished=ti[q,k,OEXITNS]>0
            reason=int(ti[q,k,OEXITREASON])
            orders.append(dict(
                model=name,group_id=groupno+1,stage=int(ti[q,k,OSTAGE]),
                entry_utc=iso(ti[q,k,OENTRYNS]),exit_utc=iso(ti[q,k,OEXITNS]),
                direction="BUY" if ti[q,k,OSIDE]==1 else "SELL",
                lot=float(tf[q,k,OLOT]),entry_quote=float(tf[q,k,OENTRY]),
                exit_quote=float(tf[q,k,OEXIT]) if finished else None,
                outcome={0:"OPEN",1:"TP",2:"SL",3:"EQUITY_STOP_OUT"}[reason],
                commission_usd=float(tf[q,k,OFEE]),
                required_margin_at_entry_usd=float(tf[q,k,OMARGIN]),
                actual_entry_spread_usd_per_oz=float(tf[q,k,OSPREAD]),
                realized_net_usd=float(tf[q,k,ONET]) if finished else None,
                holding_seconds=float((ti[q,k,OEXITNS]-ti[q,k,OENTRYNS])/1e9) if finished else None))
    gd=pd.DataFrame(groups);od=pd.DataFrame(orders)
    gd.to_csv(folder/"ALL_INDEPENDENT_H1_GROUPS.csv",index=False)
    od.to_csv(folder/"ALL_INDEPENDENT_GROUP_TICK_TRADE_ORDERS.csv",index=False)
    summaries=[];byyear=[];depth=[]
    for q,model in enumerate(MODELS):
        x=gd[gd.model==model]
        done=x[x.outcome=="TP_COMPLETED"]
        fails=x[x.outcome.isin(("BROKER_BLOCKED","EQUITY_STOP_OUT"))]
        other=x[~x.index.isin(done.index)&~x.index.isin(fails.index)]
        assert len(x)==int(s["ng"][q])
        assert len(done)+len(fails)+len(other)==len(x)
        ticket=od[od.model==model]
        assert len(ticket)==int(s["no"][q])
        # Vectorized whole-ledger reconciliation; don't perform tens of
        # thousands of O(number_of_tickets) repeated DataFrame scans.
        tp_counts=ticket[ticket.outcome=="TP"].groupby("group_id").size()
        if len(tp_counts)!=len(done) or not (tp_counts==1).all():
            raise AssertionError("Not exactly one TP ticket per completed group")
        if set(tp_counts.index)!=set(done.group_id):
            raise AssertionError("TP tickets don't exactly match TP groups")
        closed=ticket[ticket.outcome!="OPEN"].groupby("group_id").realized_net_usd.sum()
        open_fees=ticket[ticket.outcome=="OPEN"].groupby("group_id").commission_usd.sum()
        check=x.set_index("group_id")
        exp=START+closed.reindex(check.index,fill_value=0.0)-open_fees.reindex(check.index,fill_value=0.0)
        errors=(exp-check.terminal_balance_usd).abs()
        if len(errors) and float(errors.max())>1e-4:
            raise AssertionError("Funding mismatch in group "+str(errors.idxmax())+
                                 " difference "+str(errors.max()))
        pnl=done.realized_pnl_usd.to_numpy(float)
        if len(done) and float(done.realized_pnl_usd.min()) < -0.0001:
            raise AssertionError("Completed TP group must NOT realize a loss under minimum recovery lots: "+str(done.realized_pnl_usd.min()))

        summaries.append(dict(
            model=model,first_year=first,last_year=last,
            initial_capital_PER_GROUP_USD=START,
            initial_lot_per_independent_group=BASELOT,
            lot_rule="minimum break-even volume step 0.01 based on actual realized loss, nominal +$1/oz TP and $7/lot roundtrip commission",
            eligible_H1_signal_hours=int(np.count_nonzero(book)),
            launched_independent_groups=len(x),
            groups_started_with_first_tick_after_10min=int(s["rejected_late"][q]),
            groups_started_with_spread_at_least_SL=int(s["rejected_spread"][q]),
            TP_completed_groups=len(done),
            failed_or_broker_blocked_groups=len(fails),
            still_unresolved_at_dataset_end=len(other),
            win_rate_completed_over_all=float(len(done)/len(x)*100) if len(x) else None,
            total_completed_groups_pnl_usd=float(done.realized_pnl_usd.sum()),
            total_failed_groups_pnl_usd=float(fails.realized_pnl_usd.sum()),
            sum_all_group_realized_pnl_COUNTERFACTUAL_NOT_TRADABLE=float(x.realized_pnl_usd.sum()),
            average_per_group_realized_pnl_usd=float(x.realized_pnl_usd.mean()),
            median_per_group_realized_pnl_usd=float(x.realized_pnl_usd.median()),
            min_individual_group_pnl_usd=float(x.realized_pnl_usd.min()),
            max_individual_group_pnl_usd=float(x.realized_pnl_usd.max()),
            largest_lot_reached=float(x.maximum_lot_used.max()),
            max_stages_in_any_group=int(x.stages_executed.max()),
            max_independent_group_drawdown=float(x.max_group_marked_drawdown_usd.max()),
            fraction_group_completed_positive_pnl=float((done.realized_pnl_usd>0).mean()) if len(done) else None))
        for yr,part in x.groupby("entry_year"):
            complete=part[part.outcome=="TP_COMPLETED"]
            bad=part[part.outcome.isin(("BROKER_BLOCKED","EQUITY_STOP_OUT"))]
            byyear.append(dict(model=model,year=int(yr),n_groups=len(part),
                completed=len(complete),blocked_or_stopout=len(bad),
                unresolved=len(part)-len(complete)-len(bad),
                pct_completed=float(len(complete)/len(part)*100),
                sum_realized_pnl_independent_not_tradable=float(part.realized_pnl_usd.sum()),
                avg_per_group_realized_pnl=float(part.realized_pnl_usd.mean()),
                max_lot=float(part.maximum_lot_used.max()),
                worst_group_pnl=float(part.realized_pnl_usd.min())))
        for n,part in x.groupby("stages_executed"):
            depth.append(dict(model=model,stages_executed=int(n),groups=len(part),
                              tp_completed=int((part.outcome=="TP_COMPLETED").sum()),
                              failed=int(part.outcome.isin(("BROKER_BLOCKED","EQUITY_STOP_OUT")).sum())))
    pd.DataFrame(summaries).to_csv(folder/"SUMMARY_PER_INDEPENDENT_GROUP_MODEL.csv",index=False)
    pd.DataFrame(byyear).to_csv(folder/"YEARLY_BY_INDEPENDENT_H1_ENTRY.csv",index=False)
    pd.DataFrame(depth).to_csv(folder/"GROUP_DEPTH_DISTRIBUTION.csv",index=False)
    audit=dict(
        run_years=[first,last],utc_entry_hours=list(range(4,20)),
        first_H1_tick_rule="previous CLOSED H1 BID candle bullish BUY bearish SELL; doji skip",
        all_eligible_hours_treated_independently=True,
        groups_may_overlap_in_HISTORICAL_COUNTERFACTUAL_SIMULATION=True,
        groups_do_not_share_equity_margin_or_pnl=True,
        not_a_simulation_of_simultaneously_traded_one_broker_account=True,
        balance_per_independent_group=START,
        lot_sizing="MIN_BREAKEVEN, NOT DOUBLE; next lot = max(0.01, ceil(max(0, initial capital - realized group balance) / ((TP_price*100-7)*0.01)) * 0.01) using actual closed trade net loss",
        nominal_TP_net_profit_per_lot_USD=NOMINAL_TP_NET_PER_LOT,
        smallest_lot_step=LOT_STEP,
        initial_lot_each_hour=BASELOT,
        diagram_pip_price_delta_USD_oz=.10,
        requested_SL_diagram_pips=20,requested_TP_diagram_pips=40,
        TP_gold_price_USD_oz=TP,SL_gold_price_USD_oz=SL,
        lots="dynamic minimum break-even rounded up to 0.01, not doubled; usual first stages 0.01,0.01,0.02,0.03,0.04 (may vary with gaps)",
        exness_contract_oz_per_lot=100,exness_raw_assumed_commission_usd_per_lot_roundtrip=7.,
        actual_bid_ask_spread=True,first_quote_after_each_H1=True,
        no_lookahead_on_prior_candle=True,
        no_forced_friday_time_or_data_end_exit=True,
        missing_real_swap=True,missing_real_HMR_schedule=True,
        missing_real_execution_latency=True,
        no_hourly_spread_or_latency_entry_filter=True,
        immediate_reverse_on_any_SL_no_spread_deferral=True,
        same_tick_instant_stop_if_spread_at_or_above_SL=True,
        mechanical_quote_based_execution_not_broker_attached_stop_validation=True,
        XAUUSD_max_lots_day_and_night=200,
        independent_model_summaries=summaries,
        count_raw_valid_ticks=int(s["valid_ticks"][0]),
        source_zip_sha256=provenance)
    (folder/"AUDIT_METHOD_AND_SOURCE_SHA256.json").write_text(json.dumps(audit,indent=2))
    print("FINAL_INDEPENDENT_GROUPS",json.dumps(summaries),flush=True)
    print("AUDIT_OK all independently funded groups checked",flush=True)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--h1",required=True)
    ap.add_argument("--out",required=True)
    ap.add_argument("--first",type=int,default=2020)
    ap.add_argument("--last",type=int,default=2026)
    args=ap.parse_args()
    out=Path(args.out)
    out.mkdir(parents=True,exist_ok=True)
    selftest()
    base,book=h1_book(args.h1)
    st=state()
    prov=[]
    for year in range(args.first,args.last+1):
        for mo in range(1,11 if year==2026 else 13):
            mm=f"{mo:02}"
            url=f"https://ticks.ex2archive.com/ticks/XAUUSD_Raw_Spread/{year}/{mm}/Exness_XAUUSD_Raw_Spread_{year}_{mm}.zip"
            temp=out/f"{year}_{mm}.zip"
            sha,sz=download(url,temp)
            cnt=0
            with zipfile.ZipFile(temp) as arc:
                bad=arc.testzip()
                if bad: raise ValueError("Bad ZIP CRC "+str(bad))
                for member in arc.namelist():
                    if not member.lower().endswith(".csv"):
                        continue
                    with arc.open(member) as fd:
                        for df in pd.read_csv(fd,usecols=["Timestamp","Bid","Ask"],chunksize=500000):
                            dt=pd.to_datetime(df.Timestamp,utc=True,errors="coerce")
                            ok=dt.notna()&df.Bid.notna()&df.Ask.notna()
                            ns=dt[ok].astype("int64").to_numpy(np.int64)
                            if not len(ns):
                                continue
                            if np.any(ns[1:]<ns[:-1]) or (st["prev_tick"][0]>0 and ns[0]<st["prev_tick"][0]):
                                raise ValueError("Non-monotonic timestamp "+url)
                            process_batch(ns,df.Bid[ok].to_numpy(np.float64),
                                           df.Ask[ok].to_numpy(np.float64),base,book,st)
                            cnt+=len(ns)
            temp.unlink(missing_ok=True)
            prov.append(dict(year=year,month=mo,url=url,sha256=sha,zip_bytes=sz,raw_ticks=cnt))
            print("MONTH",year,mm,"ticks",cnt,
                  "total_ticks",int(st["valid_ticks"][0]),
                  "independent_groups",int(st["ng"][1]),
                  "live_virtual_paths",int(st["na"][1]),flush=True)
    write_audit(st,out,args.first,args.last,prov,book)

if __name__=="__main__":
    main()

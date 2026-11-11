"""Exact historical XAUUSD H1 previous-candle direction, linked recovery groups.

ENTRY (ONLY IF NO CURRENT GROUP): new 1h bar first tick with UTC hour 04..19
inclusive, previous FULLY CLOSED H1 BID candle Close>Open => initial BUY,
Close<Open => initial SELL, Close==Open => no trade. UTC 00..03 and
20..23 are EXCLUDED FOR GROUP ENTRIES only (existing groups continue all hours).
The prior bar can be in an excluded entry hour, as only entry hours are excluded.

ONE GROUP AT A TIME. First trade 0.10 lot. SL -5 diagram pips = -$0.50
gold-price move. Each SL immediately opens opposite side at the SL tick,
volume 0.10,0.10,0.20,0.40,0.80,1.60,... and does not close the group.
Group closes ONLY on any trade TP +10 diagram pips = +$1.00 price move.
If no TP arrives within an hour, next candle does NOT open another group.
No Friday close, daily close, group time limit, reset, or arbitrary loss stop.
If the account cannot afford the next order, record broker-blocked/bankrupt
status and do not count the incomplete group as TP-completed.

True Exness RAW Bid/Ask, 100 oz per lot, assumed $7/lot roundtrip commission,
0.10 lot opening commission $0.70. Three variants per signal:
theoretical no-margin-limit, 1:2000 margin+lot cap and stressed 1:200 margin+lot
cap. Independent reversed-signal controls are also replayed for comparison,
but ONLY PREVIOUS_H1_* represent the user's actual requested strategy.
Historical swap, latency, true news-time high margin and live rejections
are not modeled. First tick after hour rollover; missing or >10m late
first tick skipped to avoid pretending an earlier open fill was possible.
STOP-distance validity: entry spread must be <SL. After SL with spread>=SL,
mandatory reversal is pending until a spread-valid tick (no fake orders).
""" 
import argparse, hashlib, json, zipfile
from pathlib import Path
import numpy as np
import pandas as pd
import requests
from numba import njit

START = 10000.0
TP = 1.00
SL = 0.50
BASE_LOT = 0.10
COMMISSION_PER_LOT = 7.0
N = 6
MAXGROUPS = 80000
MAXORDERS = 240000
MODEL_NAMES = [
    "PREVIOUS_H1__NO_LIMIT_IDEAL",
    "PREVIOUS_H1__EXNESS_2000",
    "PREVIOUS_H1__HMR_200_STRESS",
    "REVERSED_H1_CONTROL__NO_LIMIT_IDEAL",
    "REVERSED_H1_CONTROL__EXNESS_2000",
    "REVERSED_H1_CONTROL__HMR_200_STRESS",
]
STATE_NAMES = (
    "status","side","level","entry","lot","balance","gid",
    "grp_count","ord_count","completed","blocked","bankrupt",
    "g_start","g_end","g_start_balance","g_end_balance","g_orders",
    "g_largest_lot","g_reason","g_fail_required_lot","g_fail_margin",
    "g_fail_equity","g_final_level",
    "o_group","o_level","o_entry_ns","o_exit_ns","o_side","o_lot",
    "o_entry","o_exit","o_reason","o_commission","o_net",
    "peak_equity","min_equity","max_dd","max_lot",
    "ignored_busy","ignored_spread","ignored_late",
    "prevhour","prevns","last_quote","tick_counter",
)

def make_state():
    a = {}
    a["status"] = np.zeros(N,np.int8) # 0 idle,1 live,2 broker BLOCKED,3 bankrupt,4 reversal PENDING
    a["side"] = np.zeros(N,np.int8)
    a["level"] = np.zeros(N,np.int32)
    a["entry"] = np.zeros(N)
    a["lot"] = np.zeros(N)
    a["balance"] = np.full(N,START)
    a["gid"] = np.full(N,-1,np.int64)
    for k in ("grp_count","ord_count","completed","blocked","bankrupt",
              "ignored_busy","ignored_spread","ignored_late"):
        a[k] = np.zeros(N,np.int64)
    for k in ("g_start","g_end"):
        a[k] = np.zeros((N,MAXGROUPS),np.int64)
    for k in ("g_start_balance","g_end_balance","g_largest_lot",
              "g_fail_required_lot","g_fail_margin","g_fail_equity"):
        a[k] = np.zeros((N,MAXGROUPS))
    for k in ("g_orders","g_reason","g_final_level"):
        a[k] = np.zeros((N,MAXGROUPS),np.int32)
    for k in ("o_group","o_level","o_side","o_reason"):
        a[k] = np.zeros((N,MAXORDERS),np.int32)
    for k in ("o_entry_ns","o_exit_ns"):
        a[k] = np.zeros((N,MAXORDERS),np.int64)
    for k in ("o_lot","o_entry","o_exit","o_commission","o_net"):
        a[k] = np.zeros((N,MAXORDERS))
    a["peak_equity"] = np.full(N,START)
    a["min_equity"] = np.full(N,START)
    a["max_dd"] = np.zeros(N)
    a["max_lot"] = np.zeros(N)
    a["prevhour"] = np.array([-1],np.int64)
    a["prevns"] = np.zeros(1,np.int64)
    a["last_quote"] = np.zeros(2)
    a["tick_counter"] = np.zeros(1,np.int64)
    return a

@njit
def core(t,bids,asks,book,base,
         status,side,level,entry,lot,balance,gid,
         grp_count,ord_count,completed,blocked,bankrupt,
         g_start,g_end,g_start_balance,g_end_balance,g_orders,
         g_largest_lot,g_reason,g_fail_required_lot,g_fail_margin,
         g_fail_equity,g_final_level,
         o_group,o_level,o_entry_ns,o_exit_ns,o_side,o_lot,
         o_entry,o_exit,o_reason,o_commission,o_net,
         peak_equity,min_equity,max_dd,max_lot,
         ignored_busy,ignored_spread,ignored_late,
         prevhour,prevns,last_quote,tick_counter):
    for i in range(len(t)):
        ns=t[i];bid=bids[i];ask=asks[i]
        if not (np.isfinite(bid) and np.isfinite(ask) and ask>=bid>0):
            continue
        if prevns[0]>0 and ns<prevns[0]:
            raise ValueError("Input quotes are not chronological")
        hour=ns//3600000000000
        idx=hour-base
        sig=(hour!=prevhour[0]) and (0<=idx<len(book)) and book[idx]!=0
        late=((ns//60000000000)%60)>=10
        maxbrokerlot=200.0 if 7<=hour%24<=20 else 60.0
        for q in range(N):
            signal_available=sig
            entered_this_tick=False
            for rep in range(60):
                # Check order on the actual current liquidation side.
                if status[q]==1:
                    px=bid if side[q]==1 else ask
                    movement=side[q]*(px-entry[q])
                    gain=movement*(100.0*lot[q])
                    equity=balance[q]+gain
                    stopout=equity<=0.
                    tp=(movement>=TP-1e-9)
                    sl=(movement<=-SL+1e-9)
                    if not (stopout or tp or sl):
                        break
                    k=ord_count[q]-1
                    o_exit_ns[q,k]=ns
                    o_exit[q,k]=px
                    reason=3 if stopout else (1 if tp else 2)
                    o_reason[q,k]=reason
                    o_net[q,k]=gain-o_commission[q,k]
                    balance[q]+=gain
                    g=g_id=gid[q]
                    if stopout:
                        status[q]=3;bankrupt[q]+=1
                        g_reason[q,g]=3;g_end[q,g]=ns
                        g_end_balance[q,g]=balance[q]
                        g_final_level[q,g]=level[q]+1
                        break
                    if tp:
                        status[q]=0;completed[q]+=1
                        g_reason[q,g]=1;g_end[q,g]=ns
                        g_end_balance[q,g]=balance[q]
                        g_final_level[q,g]=level[q]+1
                        gid[q]=-1
                        # One TP terminates THIS group. Next group needs a
                        # new signal on a later quote/hour, not this tick.
                        signal_available=False
                        break
                    # SL: a reversal is mandatory. If spread is already
                    # wider than the 0.50 stop, wait for first VALID quote;
                    # otherwise a broker could reject the SL level and a
                    # naive simulation would loop dozens of orders at one ns.
                    level[q]+=1
                    if ask-bid>=SL-1e-9:
                        status[q]=4  # PENDING_NEXT_ORDER, NOT group completion
                        break
                    next_direction=-side[q]
                    must_open=True
                elif status[q]==4:
                    if ask-bid>=SL-1e-9:
                        break
                    next_direction=-side[q]
                    must_open=True
                elif status[q]==0 and signal_available:
                    signal_available=False
                    if late:
                        ignored_late[q]+=1
                        break
                    if ask-bid>.55 or ask-bid>=SL-1e-9:
                        ignored_spread[q]+=1
                        break
                    g=grp_count[q]
                    if g>=MAXGROUPS:raise ValueError("Group array full")
                    grp_count[q]+=1
                    gid[q]=g
                    level[q]=0
                    g_start[q,g]=ns
                    g_start_balance[q,g]=balance[q]
                    next_direction=book[idx] if q<3 else -book[idx]
                    must_open=True
                else:
                    if sig and status[q]==1 and signal_available:
                        ignored_busy[q]+=1
                    break

                if must_open:
                    lev=0.0 if q%3==0 else (2000.0 if q%3==1 else 200.0)
                    v=BASE_LOT if level[q]<=1 else BASE_LOT*(2.0**(level[q]-1))
                    ep=ask if next_direction==1 else bid
                    c=COMMISSION_PER_LOT*v
                    immediate_float=-(ask-bid)*100.0*v
                    post_fee_equity=balance[q]-c+immediate_float
                    margin=0.0 if lev==0. else ep*100.0*v/lev
                    broker_limit=(lev>0.0 and v>maxbrokerlot+1e-10)
                    margin_reject=(lev>0.0 and post_fee_equity<margin)
                    g=gid[q]
                    if post_fee_equity<=0.:
                        status[q]=3;bankrupt[q]+=1
                        g_reason[q,g]=3;g_end[q,g]=ns
                        g_end_balance[q,g]=balance[q]
                        g_final_level[q,g]=level[q]+1
                        g_fail_required_lot[q,g]=v
                        g_fail_margin[q,g]=margin
                        g_fail_equity[q,g]=post_fee_equity
                        break
                    if broker_limit or margin_reject:
                        status[q]=2;blocked[q]+=1
                        g_reason[q,g]=2;g_end[q,g]=ns
                        g_end_balance[q,g]=balance[q]
                        g_final_level[q,g]=level[q]+1
                        g_fail_required_lot[q,g]=v
                        g_fail_margin[q,g]=margin
                        g_fail_equity[q,g]=post_fee_equity
                        break
                    k=ord_count[q]
                    if k>=MAXORDERS:raise ValueError("Trade array full")
                    ord_count[q]+=1
                    status[q]=1
                    side[q]=next_direction
                    entry[q]=ep
                    lot[q]=v
                    balance[q]-=c
                    o_group[q,k]=g+1
                    o_level[q,k]=level[q]+1
                    o_entry_ns[q,k]=ns
                    o_side[q,k]=next_direction
                    o_lot[q,k]=v
                    o_entry[q,k]=ep
                    o_commission[q,k]=c
                    g_orders[q,g]+=1
                    if v>g_largest_lot[q,g]:g_largest_lot[q,g]=v
                    if v>max_lot[q]:max_lot[q]=v
                    entered_this_tick=True
                    # Immediately check entry liquidation quote. During
                    # wide spreads it can already touch the user SL.
                    continue
                break
            else:
                raise ValueError("More than 60 instant SL reversals at same quote")

            equity=balance[q]
            if status[q]==1:
                liquidation=bid if side[q]==1 else ask
                equity+=side[q]*(liquidation-entry[q])*100.0*lot[q]
            if equity>peak_equity[q]:peak_equity[q]=equity
            if equity<min_equity[q]:min_equity[q]=equity
            dd=peak_equity[q]-equity
            if dd>max_dd[q]:max_dd[q]=dd
            if sig and status[q] in (2,3):
                pass
        prevhour[0]=hour
        prevns[0]=ns
        last_quote[0]=bid;last_quote[1]=ask
        tick_counter[0]+=1

def run_chunk(ns,bid,ask,book,base,st):
    core(ns,bid,ask,book,base,*(st[k] for k in STATE_NAMES))

def previous_h1_schedule(h1):
    """Hour indices are integer hours since Unix epoch in UTC; target
    bar's PREVIOUS completed candle is strictly hour_epoch == target-1."""
    df = pd.read_csv(h1)
    df = df[df.complete.astype(str).str.lower().isin(("true","1"))].copy()
    df = df.sort_values("hour_epoch").reset_index(drop=True)
    hours=df.hour_epoch.to_numpy(np.int64)
    op=df.bid_open.to_numpy(float)
    cl=df.bid_close.to_numpy(float)
    t=pd.to_datetime(df.hour_utc,utc=True)
    base=int(hours[0])
    book=np.zeros(int(hours[-1]-base+5),np.int8)
    used=0;no_entry_window=0;doji=0;missing=0
    for j in range(len(df)):
        target=int(hours[j])+1
        target_hour=target%24
        if not (4<=target_hour<=19):
            no_entry_window+=1
            continue
        if not (np.isfinite(op[j]) and np.isfinite(cl[j])):
            missing+=1
            continue
        if cl[j] == op[j]:
            doji+=1
            continue
        if not (0<=target-base<len(book)):
            raise ValueError("signal hour outside indexed book")
        book[target-base]=1 if cl[j]>op[j] else -1
        used+=1
    print("H1_SCHEDULE",json.dumps(dict(
        complete_hourly_candles=len(df), eligible_directional_entry_hours=used,
        bullish_buy_slots=int(np.count_nonzero(book==1)),
        bearish_sell_slots=int(np.count_nonzero(book==-1)),
        doji_skips=doji, invalid_bar_skips=missing,
        excluded_entry_hours=no_entry_window,
        entry_utc_start_hour_inclusive=4,entry_utc_end_hour_inclusive=19)),
        flush=True)
    if used<1000: raise ValueError("Unexpectedly few H1 entries - invalid H1 artifact")
    return base,book

def selftest():
    # EXACT group sequence from user's diagrams, but TP=10 and SL=5 pips;
    # 0.10 lot at 100oz/lot gives $10 TP / $5 SL, commission $0.70
    # group net when 1/2/3/4 stages close: +9.30,+3.60,+7.20,+14.40.
    base=1000;hour_ns=3600000000000
    book=np.zeros(4,np.int8)
    paths=[
       ([100.0,101.0],9.3,1),
       ([100.0,99.5,98.5],3.6,2),
       ([100.0,99.5,100.0,101.0],7.2,3),
       ([100.0,99.5,100.0,99.5,98.5],14.4,4),
    ]
    for prices,expected,stage in paths:
        for mode in range(4):
            # mode0 original BUY, mode1 reverse-control BUY,
            # mode2 original SELL (mirror), mode3 reverse-control SELL.
            book[1]=1 if mode in (0,3) else -1
            series=prices if mode in (0,1) else [200.0-x for x in prices]
            st=make_state()
            tm=np.array([hour_ns*(base+1)+k*60000000000
                         for k in range(len(series))],np.int64)
            bid=np.array(series,np.float64)
            run_chunk(tm,bid,bid,book,base,st)
            qs=range(3) if mode in (0,2) else range(3,6)
            for q in qs:
                if int(st["completed"][q])!=1:
                    raise AssertionError(("scenario did not TP",stage,mode,q))
                if int(st["g_orders"][q,0])!=stage:
                    raise AssertionError(("wrong stage count",stage,mode,q,int(st["g_orders"][q,0])))
                if abs(st["balance"][q]-START-expected)>1e-6:
                    raise AssertionError(("wrong group PnL",stage,mode,q,st["balance"][q]-START))
                sign=1 if mode in (0,1) else -1
                if int(st["o_side"][q,0])!=sign:
                    raise AssertionError("Initial signal side inverted")
    # Same group must span a second eligible H1 trigger, never duplicate.
    b=np.zeros(6,np.int8);b[1]=1;b[2]=-1;b[3]=1
    st=make_state()
    t=np.array([hour_ns*(base+1),hour_ns*(base+2),hour_ns*(base+3)],np.int64)
    prices=np.array([100.,100.1,100.2])
    run_chunk(t,prices,prices,b,base,st)
    assert all(st["grp_count"]==1), ("Duplicated group while not TP",st["grp_count"])
    assert all(st["status"]==1), ("Wrong stage lifecycle across H1",st["status"])
    print("SELFTEST_PASSED TP10 SL5 linked groups BUY SELL all 4 diagrams and no duplicate group across hours",flush=True)

def download(url,p):
    sha=hashlib.sha256();size=0
    with requests.get(url,stream=True,timeout=(30,300)) as r:
        r.raise_for_status()
        with p.open("wb") as f:
            for part in r.iter_content(1024*1024):
                if part:
                    sha.update(part);size+=len(part);f.write(part)
    if not zipfile.is_zipfile(p):raise ValueError("Invalid ZIP "+url)
    return sha.hexdigest(),size

def iso(ns):
    return str(pd.Timestamp(int(ns),unit="ns",tz="UTC")) if ns else None

def write_results(st,out,first,last,prov,book):
    groups=[];orders=[];summaries=[]
    for q,label in enumerate(MODEL_NAMES):
        for g in range(int(st["grp_count"][q])):
            r=int(st["g_reason"][q,g])
            net=float(st["g_end_balance"][q,g]-st["g_start_balance"][q,g]) if r else None
            groups.append(dict(model=label,group_id=g+1,
              start_utc=iso(st["g_start"][q,g]),end_utc=iso(st["g_end"][q,g]),
              result=("TP_COMPLETED" if r==1 else ("BROKER_BLOCKED" if r==2 else ("BANKRUPT" if r==3 else "OPEN"))),
              stages_executed=int(st["g_orders"][q,g]),
              next_mandatory_stage=int(st["g_final_level"][q,g]),
              largest_lot=float(st["g_largest_lot"][q,g]),
              balance_before=float(st["g_start_balance"][q,g]),
              balance_after=float(st["g_end_balance"][q,g]) if r else None,
              group_net_realized=net,
              required_next_lot_if_failed=float(st["g_fail_required_lot"][q,g]),
              margin_requirement_if_failed=float(st["g_fail_margin"][q,g]),
              equity_after_spread_and_commission_if_failed=float(st["g_fail_equity"][q,g])))
        for k in range(int(st["ord_count"][q])):
            closed=st["o_exit_ns"][q,k]>0
            rr=int(st["o_reason"][q,k])
            orders.append(dict(model=label,group_id=int(st["o_group"][q,k]),
              stage=int(st["o_level"][q,k]),side="BUY" if st["o_side"][q,k]==1 else "SELL",
              lot=float(st["o_lot"][q,k]),
              entry_utc=iso(st["o_entry_ns"][q,k]),
              exit_utc=iso(st["o_exit_ns"][q,k]),
              entry_quote=float(st["o_entry"][q,k]),
              exit_quote=float(st["o_exit"][q,k]) if closed else None,
              reason="TP" if rr==1 else ("SL" if rr==2 else ("STOP_OUT" if rr==3 else "OPEN")),
              commission_usd=float(st["o_commission"][q,k]),
              net_after_actual_spread_commission=float(st["o_net"][q,k]) if closed else None))
        liquidation=st["last_quote"][0] if st["side"][q]==1 else st["last_quote"][1]
        unreal=0.0
        if st["status"][q]==1:
            unreal=st["side"][q]*(liquidation-st["entry"][q])*st["lot"][q]*100.0
        eq=float(st["balance"][q]+unreal)
        summaries.append(dict(model=label,years=f"{first}_{last}",
            scheduled_prev_H1_entries=int(np.count_nonzero(book)),
            started_groups=int(st["grp_count"][q]),TP_completed=int(st["completed"][q]),
            broker_blocked_groups=int(st["blocked"][q]),bankrupt_groups=int(st["bankrupt"][q]),
            executed_orders=int(st["ord_count"][q]),
            account_balance=float(st["balance"][q]),account_marked_equity=eq,
            realized_PnL=float(st["balance"][q]-START),
            max_tick_marked_drawdown=float(st["max_dd"][q]),
            minimum_marked_equity=float(st["min_equity"][q]),
            maximum_lot_used=float(st["max_lot"][q]),
            ignored_busy_signals=int(st["ignored_busy"][q]),
            ignored_high_spread_signals=int(st["ignored_spread"][q]),
            ignored_late_signals=int(st["ignored_late"][q]),
            open_at_end=bool(st["status"][q]==1),
            reversal_pending_at_end=bool(st["status"][q]==4),
            ended_broker_blocked=bool(st["status"][q]==2),
            ended_bankrupt=bool(st["status"][q]==3),
            terminal_group_id=int(st["gid"][q]+1) if st["gid"][q]>=0 else None))
    gd=pd.DataFrame(groups);od=pd.DataFrame(orders);sdf=pd.DataFrame(summaries)
    gd.to_csv(out/"ALL_GROUPS.csv",index=False)
    od.to_csv(out/"EVERY_ORDER_EXACT_BID_ASK.csv",index=False)
    sdf.to_csv(out/"ALL_6_VARIANTS_ACCOUNT_SUMMARY.csv",index=False)
    if len(gd):
        done=gd[gd.result=="TP_COMPLETED"].copy()
        done["exit_year"]=pd.to_datetime(done.end_utc,utc=True,format="mixed").dt.year
        yp=done.groupby(["model","exit_year"]).agg(
            TP_groups=("group_id","count"),
            PnL=("group_net_realized","sum"),
            max_stages=("stages_executed","max"),
            max_lot=("largest_lot","max")).reset_index()
        yp.to_csv(out/"YEARLY_COMPLETED_GROUPS.csv",index=False)
        depth=done.groupby(["model","stages_executed"]).size().rename("groups").reset_index()
        depth.to_csv(out/"GROUP_RECOVERY_DEPTH_HISTOGRAM.csv",index=False)
    for q in range(N):
        gset=gd[gd.model==MODEL_NAMES[q]]
        closed=gset[gset.result=="TP_COMPLETED"]
        if len(closed):
            # If a complete group hits TP, every preceding trade must be SL.
            os=od[(od.model==MODEL_NAMES[q])&(od.group_id.isin(closed.group_id))]
            if int((os.reason=="TP").sum())!=len(closed):
                raise AssertionError("Not exactly one TP per completed group")
            if int((os.reason=="SL").sum())!=int(closed.stages_executed.sum())-len(closed):
                raise AssertionError("Unexpected order lifecycle in completed groups")
        # Open order includes pre-charged fee and is not prematurely counted as closed.
        model_orders=od[od.model==MODEL_NAMES[q]]
        cashcheck=START-float(model_orders.commission_usd.sum())+float(
            (model_orders.loc[model_orders.reason!="OPEN","net_after_actual_spread_commission"]+
             model_orders.loc[model_orders.reason!="OPEN","commission_usd"]).sum())
        if abs(cashcheck-st["balance"][q])>0.00001:
            raise AssertionError("Balance independent ticket reconciliation failed")
    audit=dict(first_year=first,last_year=last,ticks=int(st["tick_counter"][0]),
      TP_gold_price_usd=1.00,SL_gold_price_usd=.50,
      user_diagram_pip_price_usd=.10,
      starting_equity=START,contract_oz_per_lot=100,raw_spread_commission_per_lot_roundtrip=7.0,
      order_lots=".10,.10,.20,.40,.80,1.60,3.20,...",
      exact_bid_ask=True,instant_reverse_same_tick_after_SL_when_valid=True,
      spread_stop_distance_validity_gate=True,
      wide_spread_reversal_deferred_not_terminated=True,
      completed_groups_close_only_on_one_TP=True,
      no_forced_end_friday_time_or_daily_loss_exit=True,
      entry_signal="H1 prior fully CLOSED Bid candle close>open BUY, close<open SELL; only NEW UTC hour 04..19 eligible and only when no group open; inverted separate control",
      leverage_normal=2000,leverage_stress=200,
      max_lot_day=200,max_lot_night=60,
      no_live_HMR_calendar=True,actual_swap_included=False,
      latency_and_broker_negative_balance_protection_included=False,
      quote_source_provenance=prov)
    (out/"SOURCE_SHA256_AND_EXECUTION_AUDIT.json").write_text(json.dumps(audit,indent=2))
    print("FINAL_ALL_SIX",sdf.to_json(orient="records"),flush=True)
    print("RECONCILIATION_PASSED",flush=True)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--h1",required=True)
    p.add_argument("--out",required=True)
    p.add_argument("--first",type=int,default=2020)
    p.add_argument("--last",type=int,default=2026)
    a=p.parse_args()
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    selftest()
    base,book=previous_h1_schedule(a.h1)
    st=make_state()
    prov=[]
    for year in range(a.first,a.last+1):
        for month in range(1,11 if year==2026 else 13):
            mm=f"{month:02}"
            url=f"https://ticks.ex2archive.com/ticks/XAUUSD_Raw_Spread/{year}/{mm}/Exness_XAUUSD_Raw_Spread_{year}_{mm}.zip"
            z=out/f"{year}_{mm}.zip"
            sha,size=download(url,z)
            count=0
            with zipfile.ZipFile(z) as arc:
                bad=arc.testzip()
                if bad:raise ValueError("ZIP CRC invalid "+str(bad))
                for name in arc.namelist():
                    if not name.lower().endswith(".csv"):continue
                    with arc.open(name) as reader:
                        for df in pd.read_csv(reader,usecols=["Timestamp","Bid","Ask"],chunksize=500000):
                            time=pd.to_datetime(df.Timestamp,utc=True,errors="coerce")
                            valid=time.notna()&df.Bid.notna()&df.Ask.notna()
                            ns=time[valid].astype("int64").to_numpy(np.int64)
                            if len(ns)==0:continue
                            if np.any(ns[1:]<ns[:-1]) or (st["prevns"][0] and ns[0]<st["prevns"][0]):
                                raise ValueError("Nonmonotone archive "+url)
                            run_chunk(ns,df.Bid[valid].to_numpy(np.float64),
                                df.Ask[valid].to_numpy(np.float64),book,base,st)
                            count+=len(ns)
            z.unlink(missing_ok=True)
            prov.append(dict(year=year,month=month,url=url,sha256=sha,source_zip_bytes=size,ticks=count))
            print("MONTH_DONE",year,mm,"tick",count,"total",int(st["tick_counter"][0]),
                "H1_ideal_cash",round(float(st["balance"][0]),2),
                "H1_broker_cash",round(float(st["balance"][1]),2),
                "H1_ideal_groups",int(st["grp_count"][0]),
                "H1_broker_state",int(st["status"][1]),flush=True)
    write_results(st,out,a.first,a.last,prov,book)

if __name__=="__main__":main()

"""Seven predeclared H4 trend change confirmations, 100% causal.

Prices/indicators use only CLOSED UTC H4 Bid candles from Exness tick data.
No lookahead, no intrabar pivot repaint, entry at first quote of NEXT H4.
Method selection is fixed BEFORE replay, not optimized from its results.

0 PA_DISPLACEMENT: H4 2L/2R MSS with body >=0.65 prior ATR14
                   and close >=0.20 ATR beyond last confirmed pivot.
1 PA_TWO_BAR_ACCEPTANCE: H4 MSS with body >=0.50 ATR and break >=0.15 ATR,
                   then NEXT H4 close >=0.15 ATR on correct side of
                   pivot and progresses in same direction.
2 EMA20_50_200: EMA20/50 cross, price on right side of EMA200 and
                   EMA200 slope aligned, warmup >=200 closed H4 bars.
3 ADX_DMI14: Wilder +DI/-DI cross and ADX14>=20 and ADX non-falling,
                   warmup >=28 completed H4 bars.
4 CUSUM_MATH: normalized signed H4 returns; reference drift k=0.20
                   ATR14 and change-point threshold h=3 ATR14,
                   prior trend EWMA(20) returns signed >=0.10 ATR14,
                   warmup >=30 H4 bars.
5 DONCHIAN20: confirmed H4 close through PRIOR 20 completed bar
                   high/low; initial channel break establishes state,
                   next OPPOSITE channel break confirms trend change.
6 MACD12_26_9: H4 MACD histogram crosses zero, with MACD line
                   same sign as new trend, warmup 35 closed H4 bars.

Each method is evaluated under ALL 10 user fixed TP:SL =3:1 configs,
0.01lot, $1000 continuous account, Exness Raw Spread actual Bid/Ask,
Friday/weekend carry, TP/SL-only exits, recorded actual stop gaps.
A trend change signal is an operational definition, NOT a promise
that price will continue in the new trend direction.
"""
import numpy as np
from numba import njit
from h4_major_trend_change_rr3_ten_variants_2020_2026 import observe_h4_reversal,NS_HOUR
METHOD=0
METHOD_NAMES=['PA_DISPLACEMENT','PA_TWO_BAR_ACCEPTANCE','EMA20_50_200',
              'ADX_DMI14','CUSUM_MATH','DONCHIAN20','MACD12_26_9']

@njit
def detect_confirmed_change(t,bid,si,sf,hi,lo,gi,ex,flags,ring):
    """Persist H4 state in engine-owned arrays across streaming CSV chunks.

    si: 4-int H4 observer state, sf:8-float H4 pivots/OHLC,
    hi,lo: two-left/right completed-pivot buffers, gi: pivot counts.
    ex: 6000 floats in unused former S/R registry for ATR/indicators,
    flags: 4 ints (math state, Donchian state, event count),
    ring: 2 ints (Donchian cursor and count). These arrays have no
    other use because original S/R engine and signals are fully disabled.
    """
    period=t//(4*NS_HOUR)
    if si[0]<0:
        ex[0]=bid
        observe_h4_reversal(t,bid,si,sf,hi,lo,gi)
        return 0
    if period==si[0]:
        observe_h4_reversal(t,bid,si,sf,hi,lo,gi)
        return 0
    # Just-ended H4 bar is now fully observable at first new-H4 quote.
    H=sf[0];L=sf[1];C=sf[2];pC=sf[3];O=ex[0]
    pivH=sf[4];pivL=sf[6];oldtrend=si[2]
    count=si[1];prioratr=ex[1]
    oldfast=ex[2];oldslow=ex[3];oldbase=ex[4];oldadx=ex[8]
    raw=observe_h4_reversal(t,bid,si,sf,hi,lo,gi)
    event=0
    tr=H-L
    if pC>0.:
        d=abs(H-pC)
        if d>tr:tr=d
        d=abs(L-pC)
        if d>tr:tr=d
    if prioratr<=0.:ex[1]=tr
    else:ex[1]+= (tr-ex[1])/14.
    atr=prioratr if prioratr>0. else tr
    if atr<=0.:atr=0.00001

    # Update EMAs at only this closed-bar timestamp; no forming-bar use.
    if count==0:
        ex[2]=C;ex[3]=C;ex[4]=C
        ex[31]=C;ex[32]=C
        ex[33]=0.;ex[34]=0.
    else:
        ex[2]+=2./21.*(C-ex[2])
        ex[3]+=2./51.*(C-ex[3])
        ex[4]+=2./201.*(C-ex[4])
        ex[31]+=2./13.*(C-ex[31])
        ex[32]+=2./27.*(C-ex[32])

    if METHOD==0:
        if raw!=0:
            P=pivH if raw==1 else pivL
            body=raw*(C-O)
            breakdist=raw*(C-P)
            if count>=14 and body>=0.65*atr and breakdist>=0.20*atr:
                event=raw
            else:
                si[2]=oldtrend;si[3]-=1
    elif METHOD==1:
        pending=int(ex[20])
        if pending!=0:
            # ACCEPTANCE requires actual SECOND finished H4 candle.
            if pending*(C-ex[21])>=0.15*atr and pending*(C-ex[22])>0.:
                event=pending
                si[2]=pending
                si[3]+=1
            else:
                si[2]=int(ex[23])
            ex[20]=0.
        if raw!=0:
            if pending==0 and event==0:
                P=pivH if raw==1 else pivL
                if count>=14 and raw*(C-O)>=0.50*atr and raw*(C-P)>=0.15*atr:
                    ex[20]=raw;ex[21]=P;ex[22]=C;ex[23]=oldtrend
            if event==0:si[2]=oldtrend
            si[3]-=1
    elif METHOD==2:
        if count>=200:
            earlier=oldfast-oldslow
            now=ex[2]-ex[3]
            if earlier<=0. and now>0. and C>ex[4] and ex[4]>oldbase:
                event=1
            elif earlier>=0. and now<0. and C<ex[4] and ex[4]<oldbase:
                event=-1
    elif METHOD==3:
        if count>0 and ex[10]>0. and ex[11]>0.:
            up=H-ex[10];down=ex[11]-L
            plus=up if up>down and up>0. else 0.
            minus=down if down>up and down>0. else 0.
            if count<=14:
                ex[5]+=tr;ex[6]+=plus;ex[7]+=minus
            else:
                ex[5]+=tr-ex[5]/14.
                ex[6]+=plus-ex[6]/14.
                ex[7]+=minus-ex[7]/14.
            if ex[5]>1e-12:
                pdi=100.*ex[6]/ex[5]
                mdi=100.*ex[7]/ex[5]
                den=pdi+mdi
                dx=100.*abs(pdi-mdi)/den if den>1e-12 else 0.
                if count==15:ex[8]=dx
                elif count>15:ex[8]+=(dx-ex[8])/14.
                direction=1 if pdi>mdi else (-1 if mdi>pdi else 0)
                prior_direction=int(ex[9])
                if count>=28 and prior_direction!=0 and direction!=0 and direction!=prior_direction:
                    if ex[8]>=20. and ex[8]>=oldadx:event=direction
                ex[9]=direction
        ex[10]=H;ex[11]=L
    elif METHOD==4:
        if pC>0.:
            move=C-pC
            ex[17]+=2./21.*(move-ex[17])
            if count>=30 and flags[0]==0 and abs(ex[17])>=0.10*atr:
                flags[0]=1 if ex[17]>0. else -1
                ex[15]=0.;ex[16]=0.
            if count>=30 and flags[0]!=0:
                normalized=move/atr
                ex[15]=max(0.,ex[15]+normalized-0.20)
                ex[16]=max(0.,ex[16]-normalized-0.20)
                if flags[0]==-1 and ex[15]>=3.:event=1
                elif flags[0]==1 and ex[16]>=3.:event=-1
                if event!=0:
                    flags[0]=event
                    ex[15]=0.;ex[16]=0.
    elif METHOD==5:
        filled=int(ring[1]);pos=int(ring[0])
        if filled>=20:
            upper=-1e30;lower=1e30
            for k in range(20):
                if ex[100+k]>upper:upper=ex[100+k]
                if ex[120+k]<lower:lower=ex[120+k]
            change=0
            if C>upper:change=1
            elif C<lower:change=-1
            if change!=0 and change!=flags[1]:
                if flags[1]!=0:event=change
                flags[1]=change
        ex[100+pos]=H;ex[120+pos]=L
        ring[0]=(pos+1)%20
        if filled<20:ring[1]=filled+1
    elif METHOD==6:
        macd=ex[31]-ex[32]
        earlierhist=ex[34]
        if count<=1:ex[33]=macd
        else:ex[33]+=2./10.*(macd-ex[33])
        hist=macd-ex[33]
        if count>=35:
            if earlierhist<=0. and hist>0. and macd>0.:event=1
            elif earlierhist>=0. and hist<0. and macd<0.:event=-1
        ex[34]=hist
    # Next candle's first quote is the event's first executable price.
    ex[0]=bid
    if event!=0:flags[2]+=1
    return event

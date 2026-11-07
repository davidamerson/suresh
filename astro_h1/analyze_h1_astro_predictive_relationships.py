"""Strict chronological H1 XAUUSD close direction and volatility research.
Each astro feature is computed at first tick of candle; all market predictors shifted
from earlier completed candles except current bid_open/ask_open.
No future feature leakage, no yearly resetting, 2025+ chronological holdout.
Research objective: ASSOCIATION, independent predictive skill, and same-year date/hour recurrence.
"""
import argparse,json,math
from pathlib import Path
import numpy as np,pandas as pd
from sklearn.linear_model import Ridge,LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error,mean_squared_error,accuracy_score,roc_auc_score,log_loss
from scipy.stats import spearmanr,kruskal,pearsonr,binomtest

def evaluate(candle_path,astro_path,out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    p=pd.read_csv(candle_path)
    p=p[p.complete.astype(str).str.lower().isin(("true","1"))].copy()
    a=pd.read_csv(astro_path)
    assert len(p)==len(a)
    d=p.merge(a,on="hour_utc",validate="one_to_one",how="left")
    d["time"]=pd.to_datetime(d.hour_utc,utc=True)
    d=d.sort_values("time").reset_index(drop=True)
    assert d.time.is_monotonic_increasing
    assert d["aspect_cycle_JUPITER_SATURN_sin"].notna().all()
    d["year"]=d.time.dt.year
    d["month"]=d.time.dt.month
    d["day"]=d.time.dt.day
    d["hour"]=d.time.dt.hour
    d["dow"]=d.time.dt.dayofweek
    d["calendar_day_of_year"]=d.time.dt.dayofyear
    d["body"]=d.bid_close-d.bid_open
    d["range"]=d.bid_high-d.bid_low
    d["up"]=(d.body>0).astype(int)
    d["hour_pct"]=d.body/d.bid_open*100
    d["market_previous_body"]=d.body.shift(1)
    d["market_previous_range"]=d["range"].shift(1)
    d["market_previous_spread"]=d.open_spread_gold_usd.shift(1)
    d["market_mean24_body"]=d.body.shift(1).rolling(24,min_periods=2).mean()
    d["market_mean24_range"]=d["range"].shift(1).rolling(24,min_periods=2).mean()
    d["market_std24_body"]=d.body.shift(1).rolling(24,min_periods=2).std()
    d["market_mean120_body"]=d.body.shift(1).rolling(120,min_periods=5).mean()
    d["market_mean120_range"]=d["range"].shift(1).rolling(120,min_periods=5).mean()
    d["market_open_spread"]=d.open_spread_gold_usd
    d["market_log_open_price"]=np.log(d.bid_open)
    d["market_year"]=d.year-2020
    d["calendar_yearphase_sin"]=np.sin(2*np.pi*(d.calendar_day_of_year-1)/365.2425)
    d["calendar_yearphase_cos"]=np.cos(2*np.pi*(d.calendar_day_of_year-1)/365.2425)
    d["calendar_monthphase_sin"]=np.sin(2*np.pi*(d.month-1)/12)
    d["calendar_monthphase_cos"]=np.cos(2*np.pi*(d.month-1)/12)
    cats=pd.get_dummies(d[["hour","dow"]].astype({"hour":"category","dow":"category"}),dtype=float)
    for c in cats.columns:d["baseline_"+c]=cats[c]
    baseline=[c for c in d.columns if c.startswith("market_") or c.startswith("calendar_") or c.startswith("baseline_")]
    # Astronomical and traditional feature GROUPS, transparent rather than "every astrologer".
    allastro=[c for c in a.columns if c!="hour_utc"]
    groups={
       "ASTRO_SOLAR":[x for x in allastro if x.startswith("planet_SUN_") or x.startswith("london_sid_ascendant_") or x.startswith("lon_sun_alt_clock")],
       "ASTRO_LUNAR":[x for x in allastro if x.startswith("planet_MOON_") or x.startswith("moon_nakshatra") or x.startswith("tithi")],
       "PANCHANG":[x for x in allastro if x.startswith("moon_nakshatra") or x.startswith("tithi") or x.startswith("nitya_yoga") or x.startswith("karana")],
       "PLANETARY_ASPECTS":[x for x in allastro if x.startswith("aspect_")],
       "RETROGRADES":[x for x in allastro if x.startswith("retrograde_") or x.startswith("speed_")],
       "RAHU_HORA":[x for x in allastro if x.startswith(("lon_rahu_frac","lon_yama_frac","lon_gulika_frac","col_rahu_frac","col_yama_frac","col_gulika_frac","lon_hora_","col_hora_","ny_hora_"))],
       "NODES_SATURN":[x for x in allastro if x.startswith(("graha_drishti_","rahu_sid_aspect_","saturn_transit_")) or x in ["saturn_sidereal_sign","rahu_sidereal_sign","ketu_sidereal_sign"]],
       "ALL_ASTRO":allastro
    }
    candidates={"NO_ASTRO_CALENDAR_MARKET":baseline}
    for k,cols in groups.items():
        candidates[k+"_ONLY"]=cols
        candidates["MARKET_PLUS_"+k]=baseline+cols
    # ALL_ASTRO contains location weekday features; mechanical overlap must be interpreted cautiously.
    d[baseline]=d[baseline].replace([np.inf,-np.inf],np.nan).fillna(0)
    d[allastro]=d[allastro].replace([np.inf,-np.inf],np.nan).fillna(0)
    train=np.flatnonzero(d.year<=2024)
    test=np.flatnonzero(d.year>=2025)
    assert len(train)>15000 and len(test)>5000, (len(train),len(test))
    target=d.body.to_numpy(float)
    target_range=np.log1p(d["range"].to_numpy(float))
    up=d["up"].to_numpy(int)
    summary=[];preds={}
    # Separate locked Ridge and Logistic, alpha=150 and C=0.08, no hyperparameter search.
    for name,columns in candidates.items():
        columns=list(dict.fromkeys(columns))
        X=d[columns].to_numpy(dtype=np.float64)
        std=StandardScaler()
        # Train-only standardized clipping prevents rare near-zero-variance
        # planetary orbs from exploding 2025-26 extrapolated predictions.
        # This is a NUMERIC STABILITY correction, not a profitable signal
        # threshold fitted on the test outcomes.
        Xtr=np.clip(std.fit_transform(X[train]),-8.,8.)
        Xte=np.clip(std.transform(X[test]),-8.,8.)
        reg=Ridge(alpha=150.,fit_intercept=True)
        reg.fit(Xtr,target[train])
        pred_raw=reg.predict(Xte)
        low=float(np.quantile(target[train],.001))
        high=float(np.quantile(target[train],.999))
        yhat=np.clip(pred_raw,low,high)
        regvol=Ridge(alpha=150.,fit_intercept=True)
        regvol.fit(Xtr,target_range[train])
        vlog=regvol.predict(Xte)
        vlog=np.clip(vlog,float(np.quantile(target_range[train],.001)),
                         float(np.quantile(target_range[train],.999)))
        volhat=np.expm1(vlog)
        clf=LogisticRegression(C=0.08,max_iter=200,solver="lbfgs")
        clf.fit(Xtr,up[train])
        p_up=clf.predict_proba(Xte)[:,1]
        pred_dir=(p_up>=0.5).astype(int)
        selected=(p_up>=0.57)|(p_up<=0.43)
        side=np.where(p_up>=0.57,1,np.where(p_up<=0.43,-1,0))
        # Upper bound on execution performance. Enter at first quote and exit
        # at last quote of same H1, not exact real-time executable; commissions
        # and live slippage/HMR are not fully covered by observed raw quotes.
        bt=d.iloc[test]
        entry=np.where(side==1,bt.ask_open.to_numpy(float),bt.bid_open.to_numpy(float))
        exit_=np.where(side==1,bt.bid_close.to_numpy(float),bt.ask_close.to_numpy(float))
        gold_profit=side*(exit_-entry)-0.07*(side!=0)
        gold_profit[side==0]=0.
        result={
          "model":name,"n_market_bars":len(train),"n_test_bars":len(test),
          "n_features":len(columns),
          "h1_close_open_mae_gold_usd":float(mean_absolute_error(target[test],yhat)),
          "h1_close_open_rmse_gold_usd":float(np.sqrt(mean_squared_error(target[test],yhat))),
          "hourly_range_mae_gold_usd":float(mean_absolute_error(d["range"].to_numpy(float)[test],volhat)),
          "direction_accuracy":float(accuracy_score(up[test],pred_dir)),
          "direction_auc":float(roc_auc_score(up[test],p_up)),
          "direction_log_loss":float(log_loss(up[test],p_up)),
          "signal_trades":int(selected.sum()),
          "signal_trading_hourly_model_net_usd":float(gold_profit.sum()),
          "signal_avg_net_per_trade_usd":float(gold_profit.sum()/max(1,int(selected.sum()))),
          "2025_hourly_model_net_usd":float(gold_profit[bt.year.to_numpy()==2025].sum()),
          "2026_hourly_model_net_usd":float(gold_profit[bt.year.to_numpy()==2026].sum())
        }
        summary.append(result)
        preds[name]=pd.DataFrame({"hour_utc":bt.hour_utc.to_numpy(),"year":bt.year.to_numpy(),
            "actual_h1_body_gold":target[test],"predicted_body":yhat,
            "probability_up":p_up,"actual_range_gold":d["range"].to_numpy()[test],
            "predicted_range_gold":volhat,
            "trade_side":side,"model_net_usd":gold_profit})
        print("H1_MODEL_COMPLETE",json.dumps(result),flush=True)
    summary=pd.DataFrame(summary).sort_values("h1_close_open_mae_gold_usd")
    summary.to_csv(out/"h1_chronological_model_comparison.csv",index=False)
    for k in ("NO_ASTRO_CALENDAR_MARKET","MARKET_PLUS_ALL_ASTRO","MARKET_PLUS_ASTRO_LUNAR",
              "MARKET_PLUS_PLANETARY_ASPECTS","MARKET_PLUS_RAHU_HORA"):
        preds[k].to_csv(out/(k+"_predictions_2025_2026.csv"),index=False)
    # same month/day/hour versus previous year and same weekday/hour 52 weeks before.
    d["stamp_year_back"]=d["time"]-pd.DateOffset(years=1)
    # Feb29 maps Feb28; exclude Feb29 as unpaired.
    d.loc[(d.month==2)&(d.day==29),"stamp_year_back"]=pd.NaT
    d["stamp_52weeks_back"]=d["time"]-pd.Timedelta(days=364)
    lookup=d.set_index("time")["body"]
    previous_year=lookup.reindex(pd.DatetimeIndex(d.stamp_year_back)).to_numpy(float)
    prev52=lookup.reindex(pd.DatetimeIndex(d.stamp_52weeks_back)).to_numpy(float)
    recurrence=[]
    for label,past in [("SAME_MONTH_DAY_HOUR_PREVIOUS_YEAR",previous_year),
                        ("SAME_WEEKDAY_HOUR_52_WEEKS_EARLIER",prev52)]:
        mask=np.isfinite(past)&(d.year.to_numpy()>=2021)
        cur=target[mask];prev=past[mask]
        include=(cur!=0)&(prev!=0)
        cur=cur[include];prev=prev[include]
        n=len(cur)
        matches=int((np.sign(cur)==np.sign(prev)).sum())
        base=float((cur>0).mean()*(prev>0).mean()+(cur<0).mean()*(prev<0).mean())
        recurrence.append(dict(comparison=label,pair_count=n,same_direction_count=matches,
           same_direction_percent=100*matches/max(1,n),
           expected_agreement_if_marginal_independent_percent=100*base,
           signed_body_pearson_r=float(np.corrcoef(cur,prev)[0,1]),
           signed_body_spearman_r=float(spearmanr(cur,prev).statistic),
           indicative_binomial_p_under_independent_pairs=float(binomtest(matches,n,base).pvalue) if n>0 and 0<base<1 else None,
           caveat="Pairs overlap over years; use block controls for significance; not sufficient for year-after-year predictive claim"))
    pd.DataFrame(recurrence).to_csv(out/"same_calendar_day_same_hour_yearly_recurrence.csv",index=False)
    # Candle OHLC market hour distributions and astronomical solar/Rahu windows.
    hourstats=d.groupby(["dow","hour"],observed=True).agg(
        H1_count=("body","size"),mean_body_gold=("body","mean"),p_up=("up","mean"),
        mean_abs_body_gold=("body",lambda z:float(np.mean(np.abs(z)))),
        mean_range_gold=("range","mean")).reset_index()
    hourstats.to_csv(out/"market_hour_weekday_profile.csv",index=False)
    # Example genuine associations: relative solar daylight/local planet-hour
    # versus observed volatility; must recheck conditional on weekday/hour.
    d["range_adjusted_for_weekday_hour"]=d["range"]-d.groupby(["dow","hour"])["range"].transform("mean")
    sungroup=[]
    for loc in ("lon","col","ny"):
        state=(d[f"{loc}_daylight"]>=0.5)
        inside=(d[f"{loc}_rahu_frac"]>0)
        for name,mask in [("DAYLIGHT",state),("RAHU_H1_OVERLAP",inside)]:
            if mask.sum()<30 or (~mask).sum()<30:continue
            raw1=float(d.loc[mask,"range"].mean());raw0=float(d.loc[~mask,"range"].mean())
            adj1=float(d.loc[mask,"range_adjusted_for_weekday_hour"].mean())
            adj0=float(d.loc[~mask,"range_adjusted_for_weekday_hour"].mean())
            sungroup.append(dict(city=loc,indicator=name,n_inside=int(mask.sum()),n_outside=int((~mask).sum()),
                                mean_range_inside=raw1,mean_range_outside=raw0,
                                raw_range_ratio=raw1/raw0 if raw0 else None,
                                residual_mean_difference_after_weekday_hour=adj1-adj0))
    pd.DataFrame(sungroup).to_csv(out/"solar_daylight_rahu_hour_volatility_relationship.csv",index=False)
    # Cross-year & cross-2025/26 scores
    yearrows=[]
    for name,P in preds.items():
        for y in sorted(P.year.unique()):
            sub=P[P.year==y];valid=sub.actual_h1_body_gold!=0
            yearrows.append(dict(model=name,year=int(y),n=len(sub),
                body_mae=float(np.mean(abs(sub.actual_h1_body_gold-sub.predicted_body))),
                up_accuracy=float(np.mean((sub.probability_up>0.5)==(sub.actual_h1_body_gold>0))),
                auc=float(roc_auc_score((sub.actual_h1_body_gold>0).astype(int),sub.probability_up)),
                trades=int((sub.trade_side!=0).sum()),net=float(sub.model_net_usd.sum())))
    pd.DataFrame(yearrows).to_csv(out/"holdout_per_year_results.csv",index=False)
    discovery={
       "dataset_start":str(d.time.min()),"dataset_last":str(d.time.max()),
       "total_qualified_h1_candles":len(d),
       "train_through_utc":"2024-12-31 23:59:59 UTC",
       "test_from_utc":"2025-01-01 00:00:00 UTC",
       "mean_abs_h1_body_gold":float(np.mean(abs(d.body))),
       "test_zero_change_baseline_MAE":float(np.mean(abs(target[test]))),
       "test_up_frequency":float(up[test].mean()),
       "baseline_positive_direction_accuracy":float(max(up[test].mean(),1-up[test].mean())),
       "minute_weekday_volatility_Kruskal_p":float(kruskal(*[g["range"].to_numpy() for h,g in d.groupby("hour")]).pvalue),
       "baseline":summary[summary.model=="NO_ASTRO_CALENDAR_MARKET"].to_dict("records")[0],
       "best_astrological_model_selected_after_seeing_holdout_is_NOT_independent_validation":summary[summary.model.str.contains("ASTRO|PANCHANG|PLANETARY|RETRO|RAHU|NODES")].iloc[0].to_dict(),
       "point_in_time_integrity":"Astronomy only at first tick, past market candles shifted, test 2025-2026 never used for model fitting",
       "limitations":"Raw Exness Bid Ask, 1 oz fixed 0.01 lot, 0.07 USD commission. Research fills first and last ticks of H1 are not precise executable live orders. Swaps, outages, slippage not reconstructed. No evidence of planetary causation from a price correlation.",
       "interpretation":"Hour/day market effects and local sunrise/planetary hours are mechanically correlated. Test incremental astrology beyond calendar and market baseline, not only naive raw correlation."
    }
    (out/"evaluation_and_caveats.json").write_text(json.dumps(discovery,indent=2,default=str))
    print("HOURLY_RESEARCH_FINAL",json.dumps({
        "total_bars":len(d),"train_bars":len(train),"test_bars":len(test),
        "best5_by_body_mae":summary.head(5).to_dict("records"),
        "weekday_hour_recurrence":recurrence,
        "sun_volatility":sungroup,
        "baseline":discovery["baseline"],
        "best_astrological":discovery["best_astrological_model_selected_after_seeing_holdout_is_NOT_independent_validation"]},default=str),flush=True)
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--candles",required=True);p.add_argument("--astro",required=True);p.add_argument("--out",default="results/astro_h1_analysis")
    a=p.parse_args();evaluate(a.candles,a.astro,a.out)

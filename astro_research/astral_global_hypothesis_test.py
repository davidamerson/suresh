#!/usr/bin/env python3
"""Pre-registered astrology proxy forecasting pilot.
Read astro_research/PREREGISTERED_PROTOCOL.md before interpreting results.
Historical associations cannot establish astrology's causal or personal validity.
"""
import argparse, hashlib, io, json, time, zipfile
from pathlib import Path
import numpy as np
import pandas as pd
import requests
import swisseph as swe
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

SEED = 20261106
RUN_DATE = "2026-11-06"
swe.set_sid_mode(swe.SIDM_LAHIRI)

def get_bytes(url, params=None, timeout=200):
    sess=requests.Session()
    sess.headers.update({"User-Agent":"AstrologyScientificResearch/0.1 (historical-research; source provenance)"})
    errors=[]
    for attempt in range(4):
        try:
            r=sess.get(url, params=params, timeout=timeout)
            r.raise_for_status()
            return r.content, {"url":r.url,"nbytes":len(r.content),
                               "sha256":hashlib.sha256(r.content).hexdigest()}
        except Exception as e:
            errors.append(repr(e))
            time.sleep(min(8, 2**attempt))
    raise RuntimeError("Source download failure "+url+": "+"; ".join(errors))

def earthquakes():
    b, src = get_bytes("https://earthquake.usgs.gov/fdsnws/event/1/query",
                       {"format":"csv","starttime":"2000-01-01",
                        "endtime":"2026-01-01","minmagnitude":"7"})
    raw=pd.read_csv(io.BytesIO(b))
    if "time" not in raw or "mag" not in raw: raise ValueError("USGS schema invalid")
    t=pd.to_datetime(raw["time"],utc=True,errors="coerce")
    mag=pd.to_numeric(raw["mag"],errors="coerce")
    mask=t.notna() & (mag>=7)
    eq_dates=t.loc[mask].dt.tz_convert(None).dt.normalize()
    dates=pd.date_range("2000-01-01","2025-12-31",freq="D")
    counts=eq_dates.value_counts().reindex(dates,fill_value=0)
    y=(counts>0).astype(int)
    prior_7=y.shift(1).rolling(7,min_periods=1).sum().fillna(0).to_numpy()
    past30=y.shift(1).rolling(30,min_periods=1).sum().fillna(0).to_numpy()
    prior={"prior7_events":prior_7,"prior30_events":past30}
    src.update({"row_count":int(len(raw)),"events_m7":int(mask.sum()),
                "days_positive":int(y.sum())})
    return dates,y.to_numpy(),prior,[src],2017,"at least one worldwide M>=7 earthquake on UTC day"

def markets():
    b,src=get_bytes("https://fred.stlouisfed.org/graph/fredgraph.csv",{"id":"SP500"})
    raw=pd.read_csv(io.BytesIO(b))
    datecol=next((c for c in raw.columns if c.lower() in ("observation_date","date")),None)
    valuecol=next((c for c in raw.columns if c.upper()=="SP500"),None)
    if not datecol or not valuecol:raise ValueError("FRED SP500 CSV columns invalid: "+str(raw.columns.tolist()))
    raw["date"]=pd.to_datetime(raw[datecol],errors="coerce")
    raw["close"]=pd.to_numeric(raw[valuecol],errors="coerce")
    raw=raw.dropna(subset=["date","close"]).sort_values("date")
    raw=raw[(raw.date>="2016-11-07")&(raw.date<="2026-01-01")].copy()
    raw["return"]=raw.close.pct_change()
    raw=raw.dropna(subset=["return"])
    dates=pd.DatetimeIndex(raw.date)
    y=(raw["return"]<=-0.01).astype(int).to_numpy()
    prior_r=raw["return"].shift(1)
    r7=raw["return"].shift(1).rolling(7,min_periods=2).std()
    r20=raw["return"].shift(1).rolling(20,min_periods=5).std()
    prev_sign=raw["return"].shift(1)
    prior={"prior_daily_return":prev_sign.fillna(0).to_numpy(),
           "prior7_return_std":r7.fillna(0).to_numpy(),
           "prior20_return_std":r20.fillna(0).to_numpy()}
    src.update({"trading_days":int(len(dates)),"down_1pct_days":int(y.sum())})
    return dates,y,prior,[src],2021,"S&P 500 closes down >=1% in the same trading day (astronomy 00 UTC before US close)"

def conflicts():
    url="https://ucdp.uu.se/downloads/ged/ged261-csv.zip"
    b,src=get_bytes(url,timeout=300)
    with zipfile.ZipFile(io.BytesIO(b)) as z:
        names=[n for n in z.namelist() if n.lower().endswith(".csv")]
        if not names:raise ValueError("GED ZIP contains no CSV")
        with z.open(names[0]) as f:
            raw=pd.read_csv(f,low_memory=False,
               usecols=lambda c:c.strip().lower() in ("date_start","date_end","date_prec","best","id"))
    keys={c.lower():c for c in raw.columns}
    for k in ("date_start","date_prec","best"):
        if k not in keys:raise ValueError("GED expected column missing: "+k+", got "+str(raw.columns.tolist()))
    exact=pd.to_numeric(raw[keys["date_prec"]],errors="coerce")==1
    dates_exact=pd.to_datetime(raw.loc[exact,keys["date_start"]],errors="coerce").dt.normalize()
    deaths=pd.to_numeric(raw.loc[exact,keys["best"]],errors="coerce").clip(lower=0).fillna(0)
    days=pd.date_range("1989-01-01","2025-12-31",freq="D")
    counts=pd.Series(deaths.to_numpy(),index=dates_exact).groupby(level=0).sum()
    counts=counts.reindex(days,fill_value=0).astype(float)
    threshold=float(np.percentile(counts[days.year<=2010],90))
    if threshold==0:threshold=float(np.percentile(counts[days.year<=2010],95))
    if threshold==0:raise ValueError("GED death threshold degenerates to zero; no validated target")
    y=(counts>threshold).astype(int).to_numpy()
    hist7=counts.shift(1).rolling(7,min_periods=1).sum().fillna(0)
    hist30=counts.shift(1).rolling(30,min_periods=1).sum().fillna(0)
    prior={"log_prior7_deaths":np.log1p(hist7.to_numpy()),
           "log_prior30_deaths":np.log1p(hist30.to_numpy())}
    src.update({"total_rows":int(len(raw)),"exact_date_rows":int(exact.sum()),
                "train_death_threshold":threshold,"positive_days":int(y.sum())})
    return days,y,prior,[src],2010,"global UCDP precise-date war deaths > 1989-2010 90th percentile daily threshold"

def angular_separation(a,b):
    return np.abs((np.asarray(a)-np.asarray(b)+180.)%360.-180.)

def peak(sep, target, orb=6.):
    return np.exp(-0.5*((np.asarray(sep)-target)/orb)**2)

def astro_features(dates):
    n=len(dates)
    planet_ids={"Sun":swe.SUN,"Moon":swe.MOON,"Mercury":swe.MERCURY,
      "Venus":swe.VENUS,"Mars":swe.MARS,"Jupiter":swe.JUPITER,
      "Saturn":swe.SATURN,"Uranus":swe.URANUS,"Neptune":swe.NEPTUNE,
      "Pluto":swe.PLUTO}
    arr=np.empty((n,len(planet_ids)),dtype=float)
    moon_lat=np.empty(n,dtype=float)
    ay=np.empty(n,dtype=float)
    for i,d in enumerate(dates):
        jd=swe.julday(int(d.year),int(d.month),int(d.day),0.)
        ay[i]=swe.get_ayanamsa_ut(jd)
        for j,p in enumerate(planet_ids.values()):
            xx,_=swe.calc_ut(jd,p,swe.FLG_MOSEPH)
            arr[i,j]=xx[0]%360.
            if j==1: moon_lat[i]=xx[1]
    lon={k:arr[:,j] for j,k in enumerate(planet_ids)}
    f={}
    groups={x:[] for x in ("lunar","western","vedic","mundane","east_proxy","placebo")}
    def add(group,key,values):
        key=group+"_"+key
        f[key]=np.asarray(values,dtype=float)
        groups[group].append(key)
    phase=(lon["Moon"]-lon["Sun"])%360.
    for k in (1,2,3):
        add("lunar",f"moon_sun_phase_h{k}_sin",np.sin(np.deg2rad(phase*k)))
        add("lunar",f"moon_sun_phase_h{k}_cos",np.cos(np.deg2rad(phase*k)))
    add("lunar","moon_lat",moon_lat)
    add("lunar","near_syzygy",np.maximum(peak(phase,0,12),peak(phase,180,12)))
    for name,angles in lon.items():
        for k in (1,2):
            add("western",name+f"_longitude_h{k}_sin",np.sin(np.deg2rad(angles*k)))
            add("western",name+f"_longitude_h{k}_cos",np.cos(np.deg2rad(angles*k)))
    pairs=[("Mars","Saturn"),("Jupiter","Saturn"),("Moon","Mars"),
        ("Moon","Saturn"),("Sun","Mars"),("Venus","Mars"),
        ("Mercury","Jupiter"),("Saturn","Uranus"),("Jupiter","Uranus")]
    for a,b in pairs:
        sep=angular_separation(lon[a],lon[b])
        for target in (0,60,90,120,180):
            add("western",f"{a}_{b}_aspect_{target}",peak(sep,target,6))
    sidereal={k:(v-ay)%360. for k,v in lon.items()}
    for name in ("Sun","Moon","Mars","Jupiter","Saturn"):
        a=sidereal[name]
        add("vedic",name+"_sidereal_sin",np.sin(np.deg2rad(a)))
        add("vedic",name+"_sidereal_cos",np.cos(np.deg2rad(a)))
        add("vedic",name+"_rasi_12_harm_sin",np.sin(np.deg2rad(12*a)))
        add("vedic",name+"_rasi_12_harm_cos",np.cos(np.deg2rad(12*a)))
    moon=sidereal["Moon"]
    add("vedic","nakshatra27_sin",np.sin(np.deg2rad(27*moon)))
    add("vedic","nakshatra27_cos",np.cos(np.deg2rad(27*moon)))
    add("vedic","tithi30_sin",np.sin(np.deg2rad(30*phase)))
    add("vedic","tithi30_cos",np.cos(np.deg2rad(30*phase)))
    sep_js=angular_separation(lon["Jupiter"],lon["Saturn"])
    sep_ms=angular_separation(lon["Mars"],lon["Saturn"])
    for target in (0,90,180):
        add("mundane",f"Jupiter_Saturn_{target}",peak(sep_js,target,8))
        add("mundane",f"Mars_Saturn_{target}",peak(sep_ms,target,8))
    for k in (1,2,3):
        angle=(lon["Jupiter"]-lon["Saturn"])%360.
        add("mundane",f"JS_synodic_h{k}_sin",np.sin(np.deg2rad(k*angle)))
        add("mundane",f"JS_synodic_h{k}_cos",np.cos(np.deg2rad(k*angle)))
    # This is a generic sexagenary periodicity proxy, NOT a verified Four Pillars.
    daynum=((dates-pd.Timestamp("1984-02-04")).days).to_numpy(dtype=float)
    yearnum=(dates.year.to_numpy(dtype=float)-1984.)
    for period,v in [(60,daynum),(12,yearnum),(60,yearnum)]:
        add("east_proxy",f"cycle_{period}_on_{'days' if v is daynum else 'years'}_sin",np.sin(2*np.pi*v/period))
        add("east_proxy",f"cycle_{period}_on_{'days' if v is daynum else 'years'}_cos",np.cos(2*np.pi*v/period))
    # Fixed false-positive negative control: same math, unrelated invented cycles.
    rng=np.random.default_rng(SEED)
    for i,period in enumerate(rng.uniform(20,2200,40)):
        add("placebo",f"random_period_{i}_sin",np.sin(2*np.pi*daynum/period))
    frame=pd.DataFrame(f,index=dates)
    return frame,groups

def base_features(dates, prior):
    dayofyear=dates.dayofyear.to_numpy()
    weekday=dates.dayofweek.to_numpy()
    years=dates.year.to_numpy()
    d={"annual_sin":np.sin(2*np.pi*dayofyear/365.2425),
       "annual_cos":np.cos(2*np.pi*dayofyear/365.2425),
       "weekday_sin":np.sin(2*np.pi*weekday/7),
       "weekday_cos":np.cos(2*np.pi*weekday/7),
       "year_trend":(years-2000)/10}
    d.update(prior)
    return pd.DataFrame(d,index=dates)

def report(dataset,out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    fetch={"earthquakes":earthquakes,"markets":markets,"conflicts":conflicts}[dataset]
    dates,y,prior,src,cutoff,target=fetch()
    train=np.asarray(dates.year<=cutoff)
    test=~train
    if np.count_nonzero(test)<300 or np.sum(y[test])<10 or np.sum(y[train])<10:
        raise ValueError("Insufficient eligible positives in train/test")
    astro,groups=astro_features(dates)
    control=base_features(dates,prior)
    family=["control","lunar","western","vedic","mundane","east_proxy","all","placebo"]
    trained={}
    results=[]
    for key in family:
        if key=="control":
            x=control
        elif key=="all":
            x=pd.concat([control,astro.drop(columns=groups["placebo"])],axis=1)
        else:
            x=pd.concat([control,astro[groups[key]]],axis=1)
        if not np.isfinite(x.to_numpy()).all():raise ValueError("NaN or inf features "+key)
        m=make_pipeline(StandardScaler(),LogisticRegression(C=0.05,max_iter=4000,
                                    solver="lbfgs",random_state=SEED))
        m.fit(x.to_numpy()[train],y[train])
        pred=np.clip(m.predict_proba(x.to_numpy()[test])[:,1],1e-7,1-1e-7)
        trained[key]=pred
        at_least=np.quantile(pred,0.9)
        lift=float(y[test][pred>=at_least].mean()/np.mean(y[test]))
        results.append({"dataset":dataset,"model":key,"target":target,
              "train_to_year":cutoff,"holdout_first_year":cutoff+1,
              "train_days":int(train.sum()),"holdout_days":int(test.sum()),
              "train_event_days":int(y[train].sum()),"holdout_event_days":int(y[test].sum()),
              "test_event_rate":float(np.mean(y[test])),
              "test_roc_auc":float(roc_auc_score(y[test],pred)),
              "test_average_precision":float(average_precision_score(y[test],pred)),
              "test_brier":float(brier_score_loss(y[test],pred)),
              "top_decile_lift":lift,"n_features":int(x.shape[1])})
    r=pd.DataFrame(results)
    base_auc=float(r.loc[r.model=="control","test_roc_auc"].iloc[0])
    base_brier=float(r.loc[r.model=="control","test_brier"].iloc[0])
    r["auc_above_control"]=r.test_roc_auc-base_auc
    r["brier_skill_vs_control"]=base_brier-r.test_brier
    r.to_csv(out/"model_comparison.csv",index=False)
    # Approximate null: within-year circularly shift final holdout outcomes,
    # retaining annual incidence and within-year clustering. IMPORTANT:
    # these shifts perturb seasonal alignment; interpret conservatively.
    rng=np.random.default_rng(SEED)
    indices=np.flatnonzero(test)
    years=dates.year.to_numpy()[test]
    observed=max(float(v) for v in r.loc[r.model!="control","auc_above_control"])
    delta_null=[]
    for rep in range(300):
        shifted=y[test].copy()
        for yr in np.unique(years):
            group=np.flatnonzero(years==yr)
            if len(group)>=65:
                shift=int(rng.integers(31,len(group)-30))
                shifted[group]=np.roll(shifted[group],shift)
        if np.unique(shifted).size!=2:continue
        b_auc=roc_auc_score(shifted,trained["control"])
        null_best=max(roc_auc_score(shifted,trained[k])-b_auc for k in family if k!="control")
        delta_null.append(float(null_best))
    p_max=(1+sum(v>=observed for v in delta_null))/(1+len(delta_null))
    # A naive fixed full/new moon rate ratio for readable, predeclared
    # hypothesis; not sufficient to validate other astrology methods.
    phase_col=astro["lunar_moon_sun_phase_h1_cos"]
    fullnew=(np.abs(phase_col.to_numpy())>=np.cos(2*np.pi*2/30))
    hold_y=y[test]
    a=int(np.sum(hold_y & fullnew[test]));b=int(np.sum(fullnew[test]))-a
    c=int(np.sum(hold_y & ~fullnew[test]));d=int(np.sum(~fullnew[test]))-c
    rr=float((a/(a+b))/(c/(c+d))) if (a+b)>0 and (c+d)>0 and c else None
    summary={"created_utc":pd.Timestamp.utcnow().isoformat(),"dataset":dataset,
       "target":target,"train_end":cutoff,"test_first":cutoff+1,
       "astronomy_library":swe.version,"astronomy_engine":"Swiss Ephemeris with FLG_MOSEPH",
       "estimated_top_model_name":str(r.iloc[r.auc_above_control.argmax()].model),
       "largest_holdout_auc_uplift":observed,
       "null_max_stat_adjusted_p_approx":p_max,
       "permutation_repetitions":len(delta_null),
       "holdout_day_count":int(test.sum()),
       "holdout_positive_days":int(y[test].sum()),
       "fullnew_event_days":a,"fullnew_exposure_days":a+b,
       "other_lunar_event_days":c,"other_lunar_days":c+d,
       "fullnew_risk_ratio":rr,
       "source_files":src,
       "interpretation":"exploratory observational study; no natal astrology validation or causality"}
    (out/"summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2))
    (out/"source_provenance.json").write_text(json.dumps(src,indent=2))
    print("FINAL_RESULTS_DATASET",dataset,flush=True)
    print(r[["model","train_days","holdout_days","holdout_event_days",
            "test_roc_auc","auc_above_control","test_brier",
            "brier_skill_vs_control","top_decile_lift"]].to_string(index=False),flush=True)
    print("MAX_TEST_ASTRO_IMPROVEMENT",observed,flush=True)
    print("MAX_STAT_PERMUTATION_APPROX_P",p_max,flush=True)
    print("FULLNEW_RR",rr,"counts",a,b,c,d,flush=True)
    print("SUMMARY_JSON",json.dumps(summary),flush=True)

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--dataset",choices=["earthquakes","markets","conflicts"],required=True)
    parser.add_argument("--out",default="astro_research/results")
    args=parser.parse_args()
    report(args.dataset,args.out)

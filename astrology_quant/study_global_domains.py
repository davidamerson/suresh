"""
Cross-domain astrology calendar/planetary PROXIES vs baselines, reproducible only.
For public datasets (verified source URL + hash) execute in GitHub Actions internet runner.
DO NOT equate proxy tests with full Parashara/Jaimini/natal/dasha systems.
Runs fixed expanding-origin annual forecasting; every test year's regression uses ONLY past outcomes.
"""
import csv,io,re,json,hashlib,time,math,sys
from pathlib import Path
from datetime import datetime
import numpy as np, pandas as pd, requests, swisseph as swe
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error,mean_squared_error

OUT=Path("results/astrology_global_comparison");OUT.mkdir(parents=True,exist_ok=True)
sources=[]; unavailable=[]
def get(url):
    last=None
    for k in range(3):
        try:
            r=requests.get(url,timeout=40,headers={"User-Agent":"Mozilla/5.0 Astrology Quantitative Research 2026"})
            r.raise_for_status()
            sources.append({"url":url,"sha256":hashlib.sha256(r.content).hexdigest(),"bytes":len(r.content),"retrieved_utc":datetime.utcnow().isoformat()+"Z"})
            print("DOWNLOADED",url,"bytes",len(r.content),"SHA256",sources[-1]["sha256"],flush=True)
            return r
        except Exception as e:
            last=str(e);time.sleep(k+1)
    raise RuntimeError(url+" "+str(last))

def worldbank():
    url="https://api.worldbank.org/v2/country/WLD/indicator/NY.GDP.MKTP.KD.ZG?format=json&per_page=150"
    info=get(url).json()[1]
    data={int(q["date"]):float(q["value"]) for q in info if q["value"] is not None and int(q["date"])<=2025}
    return "GLOBAL_GDP_GROWTH_PCT",data,"World Bank GDP growth (annual %) WLD"

def owid(slug,domain,name):
    url="https://ourworldindata.org/grapher/"+slug+".csv"
    df=pd.read_csv(io.BytesIO(get(url).content))
    print("COLUMNS",name,df.columns.tolist()[:20], "entities", df.iloc[:3,0].tolist(),flush=True)
    cols=list(df.columns)
    entity=next((c for c in cols if c.lower()=="entity"),cols[0])
    year=next((c for c in cols if c.lower()=="year"),"Year")
    # EM-DAT chart labels global total as "All disasters", not "World".
    key="all disasters" if domain=="natural" else "world"
    subset=df[df[entity].astype(str).str.strip().str.casefold()==key].copy()
    possible=[c for c in subset.columns if c not in (entity,year,"Code")]
    if not possible:raise ValueError("No outcome columns "+str(df.columns))
    if domain=="natural":
        if len(possible)!=1:raise ValueError("Disaster chart unexpected columns "+str(possible))
        target=possible[0]
        vals=pd.to_numeric(subset[target],errors="coerce")
        detail="total all-disaster events (Entity=All disasters)"
    elif domain=="armed":
        # UCDP chart separates 5 mutually defined conflict classes; world total
        # is the sum of those five categories for each year.
        expected=["One-sided violence","Extrasystemic","Non-state","Intrastate","Interstate"]
        if any(c not in possible for c in expected):raise ValueError("Expected 5 UCDP conflict types "+str(possible))
        vals=subset[expected].apply(pd.to_numeric,errors="coerce").fillna(0).sum(axis=1)
        detail="sum of 5 conflict classes, global World entity"
    else: raise ValueError("Unknown OWID domain")
    data={int(z):float(v) for z,v in zip(subset[year],vals) if pd.notna(v) and int(z)<=2025}
    if len(data)<20:raise ValueError("Not enough global observations "+str(len(data)))
    print("OWID_CHOSEN",name,detail,len(data),"first",list(data.items())[:3],"last",list(data.items())[-3:],flush=True)
    return name,data,"OWID "+slug+" ("+detail+")"

def stocks():
    url="https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/histretSP.html"
    from bs4 import BeautifulSoup
    soup=BeautifulSoup(get(url).text,"html.parser")
    data={};gold={}
    for tr in soup.select("tr"):
        cells=[t.get_text(" ",strip=True) for t in tr.find_all(["td","th"],recursive=False)]
        if not cells or not re.fullmatch(r"19\d{2}|20\d{2}",cells[0]):continue
        yy=int(cells[0]); percentages=[]
        for cell in cells[1:]:
            m=re.search(r"([−\-+]?\s*\d+(?:\.\d+)?)\s*%",cell)
            if m: percentages.append(float(m.group(1).replace("−","-").replace(" ","")))
        if percentages and 1928<=yy<=2025:
            data[yy]=percentages[0]
            if len(percentages)>=7 and yy>=1971:
                gold[yy]=percentages[6]
    print("DAMODARAN_PARSE",len(data),len(gold),list(data.items())[:2],list(data.items())[-2:],flush=True)
    if len(data)<50:raise RuntimeError("Damodaran stock table parsing failed")
    result=[("SP500_ANNUAL_TOTAL_RETURN_PCT",data,"NYU Stern Damodaran nominal S&P500 annual total return")]
    if len(gold)>=30: result.append(("GOLD_ANNUAL_RETURN_PCT",gold,"NYU Stern Damodaran annual gold % return"))
    return result

def coups():
    url="https://jonathanmpowell.com/wp-content/uploads/2026/08/pt_20260829.csv"
    raw=get(url).content
    d=pd.read_csv(io.BytesIO(raw),encoding="latin1")
    print("COUP_COLUMNS",d.columns.tolist(), "rows",len(d),flush=True)
    yearcol=next((k for k in d.columns if "year" in k.lower()),None)
    if yearcol is None:
        dtcol=next((k for k in d.columns if "date" in k.lower()),None)
        if dtcol:
            yrs=pd.to_datetime(d[dtcol],errors="coerce").dt.year
        else: raise ValueError("No year/date column in coup dataset")
    else:yrs=pd.to_numeric(d[yearcol],errors="coerce")
    data={}
    for yr in yrs.dropna().astype(int).tolist():
        if 1950<=yr<=2025:data[yr]=data.get(yr,0)+1
    if len(data)<30:raise ValueError("Coup dates incomplete")
    # Missing year means zero attempted coups in this event registry, once timeline is continuous.
    data={y:float(data.get(y,0)) for y in range(1950,2026)}
    return "WORLD_COUP_ATTEMPTS",data,"Powell & Thyne reported successful and failed coup attempts"

def cyc(x,p):
    a=2*np.pi*x/p
    return [np.sin(a),np.cos(a)]
def signaspect(a,b,p):
    distance=(b-a)%12+1
    return float(distance in {"Mars":(4,7,8),"Jupiter":(5,7,9),"Saturn":(3,7,10)}.get(p,(7,)))
def jaimini(a,b):
    if a==b:return 0.
    x,y=a%3,b%3
    if x==0 and y==1 and (b-a)%12!=1:return 1.
    if x==1 and y==0 and (b-a)%12!=11:return 1.
    if x==2 and y==2:return 1.
    return 0.

def astro_features(yy):
    result={}
    names=["WESTERN_ASPECTS","PARASHARA_DRISHTI","JAIMINI_RASI_DRISHTI",
           "NAKSHATRA_TRANSIT","CHINESE_60_YEAR","MAYA_TZOLKIN_HAAB",
           "MUNDANE_GREAT_CONJ","HELLENISTIC_INGRESS"]
    for n in names:result[n]=[]
    bodies={"Sun":swe.SUN,"Moon":swe.MOON,"Mars":swe.MARS,"Jupiter":swe.JUPITER,
            "Saturn":swe.SATURN,"Venus":swe.VENUS,"Mercury":swe.MERCURY,
            "Neptune":swe.NEPTUNE,"Node":swe.MEAN_NODE}
    pairs=[("Jupiter","Saturn"),("Mars","Saturn"),("Venus","Jupiter"),("Sun","Moon"),("Saturn","Node"),("Jupiter","Neptune")]
    swe.set_sid_mode(swe.SIDM_LAHIRI,0,0)
    for year in yy:
        groups={k:[] for k in names}
        for month in range(1,13):
            jd=swe.julday(int(year),month,15,12)
            trop={name:swe.calc_ut(jd,p,swe.FLG_MOSEPH)[0][0] for name,p in bodies.items()}
            sid={name:swe.calc_ut(jd,p,swe.FLG_MOSEPH|swe.FLG_SIDEREAL)[0][0] for name,p in bodies.items()}
            signs={name:int(angle/30)%12 for name,angle in sid.items()}
            west=[v for a,b in pairs for v in cyc(trop[a]-trop[b],360)]
            groups["WESTERN_ASPECTS"].append(west)
            groups["PARASHARA_DRISHTI"].append([signaspect(signs[src],signs[dst],src) for src in ["Mars","Jupiter","Saturn"] for dst in ["Sun","Moon"]])
            groups["JAIMINI_RASI_DRISHTI"].append([jaimini(signs[src],signs[dst]) for src in ["Mars","Jupiter","Saturn"] for dst in ["Sun","Moon"]])
            nak=int(sid["Moon"]/(360./27))%27
            groups["NAKSHATRA_TRANSIT"].append(cyc(nak,27)+cyc(sid["Moon"],360)+cyc(sid["Jupiter"],360))
            sep=abs(((trop["Jupiter"]-trop["Saturn"]+180)%360)-180)
            groups["MUNDANE_GREAT_CONJ"].append([float(sep<=6),float(abs(sep-90)<=6),float(abs(sep-120)<=6),float(abs(sep-180)<=6)])
        for name in ["WESTERN_ASPECTS","PARASHARA_DRISHTI","JAIMINI_RASI_DRISHTI","NAKSHATRA_TRANSIT","MUNDANE_GREAT_CONJ"]:
            result[name].append(np.array(groups[name]).mean(axis=0).tolist())
        yearphase=int(year)-1984
        result["CHINESE_60_YEAR"].append(cyc(yearphase,10)+cyc(yearphase,12)+cyc(yearphase,60))
        jdn=int(swe.julday(int(year),1,1,0)+0.5)
        result["MAYA_TZOLKIN_HAAB"].append(cyc(jdn-584283,260)+cyc(jdn-584283,365))
        jd=swe.julday(int(year),3,21,12)
        march={name:swe.calc_ut(jd,p,swe.FLG_MOSEPH)[0][0] for name,p in bodies.items()}
        result["HELLENISTIC_INGRESS"].append(cyc(march["Jupiter"],360)+cyc(march["Saturn"],360)+cyc(march["Mars"],360))
    result={k:np.array(v,dtype=float) for k,v in result.items()}
    result["ALL_FAMILIES_COMBINED"]=np.column_stack(list(result.values()))
    return result

def test_target(name,data,definition):
    # Fix holdout from final 25 calendar years, or after 2014 for short conflict series.
    years=np.array(sorted(data)); y=np.array([data[i] for i in years],dtype=float)
    if len(y)<30:raise ValueError("insufficient observations "+name)
    if (np.diff(years)!=1).any():
        first=years[0]; last=years[-1];years=np.arange(first,last+1)
        if any(int(yr) not in data for yr in years):raise ValueError("Gapped time series "+name)
        y=np.array([data[int(i)] for i in years],dtype=float)
    allfeat=astro_features(years)
    eligible=np.arange(2,len(years))
    cutoff=2015 if years[0]<=1989 else int(years[0]+round((years[-1]-years[0])*0.72))
    cutoff=max(int(years[0])+25,min(int(years[-1])-7,cutoff))
    test=eligible[years[eligible]>=cutoff]
    # fully sequential "rolling-origin": train excludes test year and ALL later outcomes
    if len(test)<7:raise ValueError("Holdout too small")
    lag=np.column_stack([y[eligible-1],y[eligible-2],(years[eligible]-years[0])/100])
    keys=["BASE_HISTORICAL_MEAN","BASE_LAG_TREND"]+list(allfeat)+["EQUAL_WEIGHT_FAMILY_ENSEMBLE"]
    predictions={k:[] for k in keys}
    # fixed, no post-hoc hyperparameter sweep
    for target_idx in test:
        tr=eligible[eligible<target_idx]
        trloc=np.where(np.isin(eligible,tr))[0]; index=int(np.where(eligible==target_idx)[0][0])
        ytr=y[tr]
        predictions["BASE_HISTORICAL_MEAN"].append(float(ytr.mean()))
        def reg(ff):
            Z=lag if ff is None else np.column_stack([lag,ff[eligible]])
            sc=StandardScaler().fit(Z[trloc])
            x=sc.transform(Z)
            m=Ridge(alpha=80.).fit(x[trloc],ytr)
            return float(m.predict(x[index:index+1])[0])
        baseline=reg(None)
        predictions["BASE_LAG_TREND"].append(baseline)
        one=[]
        for key in allfeat:
            p=reg(allfeat[key])
            predictions[key].append(p)
            if key!="ALL_FAMILIES_COMBINED":one.append(p)
        predictions["EQUAL_WEIGHT_FAMILY_ENSEMBLE"].append(float(np.mean(one)))
    truth=y[test]
    baseline=np.array(predictions["BASE_LAG_TREND"])
    baseline_err=float(np.mean(abs(truth-baseline)))
    rows=[]
    for key in keys:
        p=np.array(predictions[key])
        mae=float(np.mean(abs(truth-p)))
        rmse=float(np.sqrt(np.mean((truth-p)**2)))
        rows.append(dict(domain=name,metric="Annual count or percent",model=key,start=int(years[test[0]]),end=int(years[test[-1]]),
                         test_n=len(test),mae=round(mae,6),rmse=round(rmse,6),
                         skill_vs_lag_trend_pct=round(100*(baseline_err-mae)/baseline_err,3) if baseline_err else None,
                         skill_vs_mean_pct=round(100*(np.mean(abs(truth-np.array(predictions["BASE_HISTORICAL_MEAN"])))-mae)/np.mean(abs(truth-np.array(predictions["BASE_HISTORICAL_MEAN"]))),3),
                         family_features=(allfeat[key].shape[1] if key in allfeat else 0)))
    for i,k in enumerate(test):
        record={"domain":name,"year":int(years[k]),"actual":float(truth[i])}
        record.update({key:round(float(predictions[key][i]),6) for key in keys})
        all_predictions.append(record)
    print("DATASET_COMPLETE",name,"points",len(data),"holdout",len(test),
          "mean_base",round(rows[0]["mae"],4),"lag_base",round(rows[1]["mae"],4),
          "BEST",sorted(rows,key=lambda z:z["mae"])[:4],flush=True)
    return rows

all_results=[];all_predictions=[]
data_sources=[
    ("WB_GDP",worldbank),
    ("OWID_DISASTERS",lambda:owid("number-of-natural-disaster-events","natural","WORLD_REPORTED_NATURAL_DISASTERS")),
    ("OWID_WARS",lambda:owid("number-of-armed-conflicts","armed","WORLD_ARMED_CONFLICTS")),
    ("STOCKS",stocks),
    ("COUPS",coups)
]
for label,fn in data_sources:
    try:
        ans=fn()
        datasets=ans if isinstance(ans,list) else [ans]
        for name,data,info in datasets:
            if data:
                all_results += test_target(name,data,info)
    except Exception as e:
        msg={"dataset":label,"error":str(e)}
        unavailable.append(msg)
        print("UNAVAILABLE",json.dumps(msg),flush=True)

if not all_results: raise RuntimeError("All data sources failed; no unverifiable performance claims")
pd.DataFrame(all_results).to_csv(OUT/"all_domain_model_metrics.csv",index=False)
pd.DataFrame(all_predictions).to_csv(OUT/"all_yearly_predictions.csv",index=False)
summary={"n_completed_domains":len(set(x["domain"] for x in all_results)),
         "domains":sorted(set(x["domain"] for x in all_results)),
         "unavailable":unavailable,
         "models_per_domain":len(set(x["model"] for x in all_results)),
         "total_models_tested":len(all_results),
         "data_source_provenance":sources,
         "limitations":["Eight astronomical/calendar feature groups are mathematical proxies, not full traditional predictive systems",
                        "All 2020-2025 historical results have been visible in past research; not preregistered forward live evidence",
                        "Annual outcome averages do NOT prove ability to predict exact dates/places, individual destinies or war starts",
                        "Other forecasting covariates such as real-time macro, seismology, economics, weather and polling are omitted",
                        "A best-performing model selected after seeing test performance is not independent evidence",
                        "In-sample tuning/feature choice and multiple comparisons make naive statistical significance invalid"],
         "method":"For each holdout calendar year, refit with only earlier years, Ridge alpha=80 standardized using train alone; baseline lag-1 lag-2 linear year trend; same model complexity rules across domains.",
         "samples_per_year":12,"last_complete_year":2025}
(OUT/"provenance_and_limits.json").write_text(json.dumps(summary,indent=2,ensure_ascii=False))
print("FINAL_DOMAINS",json.dumps(summary,ensure_ascii=False),flush=True)
for domain in summary["domains"]:
    scores=sorted([x for x in all_results if x["domain"]==domain],key=lambda z:z["mae"])
    print("FINAL_RANKING",domain,json.dumps(scores,ensure_ascii=False),flush=True)

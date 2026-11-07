"""Astronomical/astrological predictors available at an XAUUSD H1 candle OPEN.
Uses Swiss Ephemeris, Lahiri sidereal, London/Colombo location and precise sunrise/sunset.
NO candle CLOSE, High, Low, later ticks or economic event outcomes used in these features.
These are operational proxies, NOT certified traditional natal/Dasha calculations.
"""
from datetime import timedelta
from functools import lru_cache
from zoneinfo import ZoneInfo
import math
import numpy as np,pandas as pd,swisseph as swe
from astral import Observer
from astral.sun import sun as astronomical_sun

SUN=swe.SUN;MOON=swe.MOON
BODIES={"SUN":SUN,"MOON":MOON,"MERCURY":swe.MERCURY,"VENUS":swe.VENUS,
        "MARS":swe.MARS,"JUPITER":swe.JUPITER,"SATURN":swe.SATURN,
        "URANUS":swe.URANUS,"NEPTUNE":swe.NEPTUNE,
        "RAHU":swe.MEAN_NODE}
ASPECT_PAIRS=[("SUN","MOON"),("MOON","MARS"),("MOON","SATURN"),
              ("MERCURY","MARS"),("MERCURY","JUPITER"),("VENUS","JUPITER"),
              ("VENUS","SATURN"),("MARS","SATURN"),("MARS","JUPITER"),
              ("JUPITER","SATURN"),("SATURN","RAHU"),("MARS","RAHU"),
              ("JUPITER","RAHU"),("SUN","SATURN"),("SUN","RAHU")]
LONDON=Observer(latitude=51.5074,longitude=-0.1278)
COLOMBO=Observer(latitude=6.9271,longitude=79.8612)
NEWYORK=Observer(latitude=40.7128,longitude=-74.006)
CITIES={"lon":(LONDON,"Europe/London"),"col":(COLOMBO,"Asia/Colombo"),
        "ny":(NEWYORK,"America/New_York")}
RAHU=[2,7,5,6,4,3,8]  # Monday=0
YAMA=[4,3,2,1,7,6,5]
GULIKA=[6,5,4,3,2,1,7]
# Weekday lords Sun..Sat Sunday first; arranged Monday -> Moon.
DAY_LORD=["MOON","MARS","MERCURY","JUPITER","VENUS","SATURN","SUN"]
CHALDEAN=["SATURN","JUPITER","MARS","SUN","VENUS","MERCURY","MOON"]
PLANET_CODE={p:i for i,p in enumerate(CHALDEAN)}

def sincos(value,prefix,period,out):
    ang=2*math.pi*float(value)/period
    out[prefix+"_sin"]=math.sin(ang)
    out[prefix+"_cos"]=math.cos(ang)

@lru_cache(maxsize=14000)
def sun_times(city,day):
    ob,tz=CITIES[city]
    s=astronomical_sun(ob,date=day,tzinfo=ZoneInfo(tz))
    return s["sunrise"],s["sunset"]

def local_periods(ts,city):
    """Vedic/local weekday counted from sunrise; proper location-specific daytime divisions."""
    _ob,tz=CITIES[city]
    local=ts.to_pydatetime().astimezone(ZoneInfo(tz))
    today=local.date()
    rise,setting=sun_times(city,today)
    if local<rise:
        today=today-timedelta(days=1)
        rise,setting=sun_times(city,today)
    next_rise,_=sun_times(city,today+timedelta(days=1))
    wd=today.weekday()
    daylight=(setting-rise).total_seconds()
    day_frac=(local-rise).total_seconds()/daylight
    daylight_now=0<=day_frac<1
    part=min(7,max(0,int(day_frac*8))) if daylight_now else -1
    hora_day=0
    if daylight_now:hora_day=min(11,int(day_frac*12))
    else:
        night_frac=(local-setting).total_seconds()/(next_rise-setting).total_seconds()
        hora_day=12+min(11,max(0,int(night_frac*12)))
    lord=PLANET_CODE[DAY_LORD[wd]]
    hora=(lord+hora_day)%7
    # Overlap fraction of upcoming UTC hour and proper locally computed daytime segment.
    candle_start=local
    candle_end=local+timedelta(hours=1)
    def overlap(segment):
        b=rise+timedelta(seconds=(segment-1)*daylight/8)
        e=rise+timedelta(seconds=segment*daylight/8)
        return max(0.,(min(candle_end,e)-max(candle_start,b)).total_seconds())/3600.
    return {
      f"{city}_rahu_frac":overlap(RAHU[wd]),
      f"{city}_yama_frac":overlap(YAMA[wd]),
      f"{city}_gulika_frac":overlap(GULIKA[wd]),
      f"{city}_daylight":float(daylight_now),
      f"{city}_hora_planet":float(hora),
      f"{city}_local_hour":float(local.hour),
      f"{city}_sun_alt_clock":float(day_frac),
      f"{city}_weekday_sunrise":float(wd)
    }

def aspect_distance(a,b,angle):
    sep=abs(((a-b+180)%360)-180)
    return abs(sep-angle)

def features_at(ts):
    """Timestamp must be the first actual quote within the hourly candle."""
    swe.set_sid_mode(swe.SIDM_LAHIRI,0,0)
    jd=swe.julday(ts.year,ts.month,ts.day,
                  ts.hour+ts.minute/60+ts.second/3600+ts.microsecond/3.6e9)
    t={};sid={};speed={}
    for name,p in BODIES.items():
        xx=swe.calc_ut(jd,p,swe.FLG_MOSEPH|swe.FLG_SPEED)[0]
        t[name]=float(xx[0]);speed[name]=float(xx[3])
        sid[name]=float(swe.calc_ut(jd,p,swe.FLG_MOSEPH|swe.FLG_SIDEREAL)[0][0])
    out={}
    # Western tropical longitude harmonics (known before financial hour).
    for name in ["SUN","MOON","MERCURY","VENUS","MARS","JUPITER","SATURN","RAHU"]:
        sincos(t[name],"planet_"+name,360.,out)
    # Most common Western major-aspect candidates with orb, phase/distance geometry.
    for a,b in ASPECT_PAIRS:
        sep=abs(((t[a]-t[b]+180)%360)-180)
        sincos(t[a]-t[b],"aspect_cycle_"+a+"_"+b,360.,out)
        for angle in (0,90,120,180):
            d=abs(sep-angle)
            out[f"aspect_{a}_{b}_{angle}_orb6"]=math.exp(-0.5*(d/6)**2)
    # Vedic Panchanga: Lahiri sidereal, 27 lunar mansions, 30 Tithis,
    # 27 Nitya Yogas, 60 Karana portions.
    nm=(sid["MOON"]/(360/27))%27
    relative=(sid["MOON"]-sid["SUN"])%360
    tithi=relative/12.
    yoga=((sid["MOON"]+sid["SUN"])%360)/(360/27)
    karana=relative/6.
    sincos(nm,"moon_nakshatra27",27,out)
    sincos(tithi,"tithi30",30,out)
    sincos(yoga,"nitya_yoga27",27,out)
    sincos(karana,"karana60",60,out)
    out["moon_nakshatra_index"]=math.floor(nm)
    out["tithi_index"]=math.floor(tithi)
    out["yoga_index"]=math.floor(yoga)
    out["karana_index"]=math.floor(karana)
    out["moon_sidereal_sign"]=math.floor(sid["MOON"]/30)%12
    out["saturn_sidereal_sign"]=math.floor(sid["SATURN"]/30)%12
    out["rahu_sidereal_sign"]=math.floor(sid["RAHU"]/30)%12
    out["ketu_sidereal_sign"]=(out["rahu_sidereal_sign"]+6)%12
    # Graha drishti only for mobile Mars 4/7/8, Jupiter 5/7/9, Saturn 3/7/10.
    for p,sights in (("MARS",(4,7,8)),("JUPITER",(5,7,9)),("SATURN",(3,7,10))):
        a=int(sid[p]/30)%12
        for q in ("MOON","SUN","RAHU"):
            b=int(sid[q]/30)%12
            dist=(b-a)%12+1
            out[f"graha_drishti_{p}_{q}"]=float(dist in sights)
    # Mean lunar node: Ketu exactly opposite Rahu; dasha not defined without natal reference.
    for q in ("SUN","MOON","MARS","SATURN","JUPITER"):
        sincos(sid["RAHU"]-sid[q],"rahu_sid_aspect_"+q,360,out)
    # Saturn relative transit to Moon is not natal sade-sati.
    out["saturn_transit_moon_neighbor_sign"]=float((int(sid["SATURN"]/30)-int(sid["MOON"]/30))%12 in (0,1,11))
    # Direct actual retrograde / longitudinal speed rather than lookahead labels.
    for p in ("MERCURY","VENUS","MARS","JUPITER","SATURN"):
        out["retrograde_"+p]=float(speed[p]<0)
        out["speed_"+p]=speed[p]
    # Angular topology/local sky at London (not individual client's birthplace).
    _cusps,asc=swe.houses_ex(jd,51.5074,-0.1278,b'P',swe.FLG_SIDEREAL)
    sincos(asc[0],"london_sid_ascendant",360,out)
    for city in ("lon","col","ny"):
        out.update(local_periods(ts,city))
    for city in ("lon","col","ny"):
        hora=int(out[f"{city}_hora_planet"])
        for k in range(7):out[f"{city}_hora_{CHALDEAN[k]}"]=float(hora==k)
    return out

def build(candles,out):
    df=pd.read_csv(candles)
    df=df[df.complete.astype(str).str.lower().isin(["true","1"])].copy()
    times=pd.to_datetime(df.hour_utc,utc=True)
    # first tick within hour; solar feature at the first tick time.
    times=times+pd.to_timedelta((df.first_quote_ns.astype("int64")-df.hour_epoch.astype("int64")*3600000000000)/1e9,unit="s")
    records=[]
    for k,ts in enumerate(times):
        rec={"hour_utc":df.hour_utc.iloc[k]}
        rec.update(features_at(ts))
        records.append(rec)
        if (k+1)%3000==0:print("ASTRO_FEATURE_PROGRESS",k+1,"of",len(times),flush=True)
    astro=pd.DataFrame.from_records(records)
    astro.to_csv(out,index=False)
    print("ASTRO_FEATURES_VERIFIED",len(astro),"columns",len(astro.columns),flush=True)
    assert len(astro)==len(df)
    assert astro.hour_utc.is_unique
    assert astro.drop(columns=["hour_utc"]).notna().all().all()
    return astro

if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser();p.add_argument("--candles",required=True);p.add_argument("--out",required=True)
    a=p.parse_args();build(a.candles,a.out)

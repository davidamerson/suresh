#include <bits/stdc++.h>
using namespace std;

static constexpr double ENTRY_DIST = 2.0;
static constexpr int WIDEN_AFTER = 5;
static constexpr double WIDE_DIST = 6.0;
static constexpr double TARGET = 0.70;
static constexpr double COMM_SIDE = 0.035; // 0.01 lot Raw Spread: $3.50/lot/side => $0.035/side

struct DayState {
    int y=0,m=0,d=0;
    bool active=false, emitted=false, ref_set=false, done=false;
    double ref_mid=0.0;
    int pos=0; // +1 buy, -1 sell, 0 flat
    double entry_price=0.0, entry_mid=0.0;
    double realized=0.0;
    int reversals=0;
    double min_liq=0.0;
    double last_bid=0.0,last_ask=0.0,last_mid=0.0;
    int last_sec=-1;
    string entry_side="";
    string exit_reason="";
    bool target_hit=false;
};

int weekday_mon0(int y,int m,int d){
    // Sakamoto: 0=Sunday..6=Saturday
    static int t[] = {0,3,2,5,0,3,5,1,4,6,2,4};
    int yy=y; if(m<3) yy-=1;
    int w=(yy + yy/4 - yy/100 + yy/400 + t[m-1] + d)%7;
    if(w==0) return 6; // Sunday -> 6
    return w-1;        // Monday -> 0
}

string daystr(int y,int m,int d){
    char b[16]; snprintf(b,sizeof(b),"%04d-%02d-%02d",y,m,d); return b;
}
string timestr(int sec){
    if(sec<0) return "";
    int h=sec/3600, mi=(sec%3600)/60, s=sec%60;
    char b[16]; snprintf(b,sizeof(b),"%02d:%02d:%02d",h,mi,s); return b;
}

inline double open_pnl(const DayState& s,double bid,double ask){
    if(s.pos==1) return bid - s.entry_price;     // 0.01 lot XAU = 1 oz
    if(s.pos==-1) return s.entry_price - ask;
    return 0.0;
}
inline double liquidation(const DayState& s,double bid,double ask){
    if(s.pos==0) return s.realized;
    return s.realized + open_pnl(s,bid,ask) - COMM_SIDE;
}

void emit_header(){
    cout << "date,target_hit,final_pnl,reversals,min_liq,entry_side,exit_reason,exit_time\n";
}
void emit_day(DayState& s,double final_pnl,const string& reason,int sec,bool target){
    if(s.emitted || !s.active) return;
    s.emitted=true; s.done=true; s.target_hit=target; s.exit_reason=reason;
    cout.setf(ios::fixed); cout<<setprecision(6)
        << daystr(s.y,s.m,s.d) << "," << (target?1:0) << "," << final_pnl << ","
        << s.reversals << "," << s.min_liq << "," << s.entry_side << ","
        << reason << "," << timestr(sec) << "\n";
}

void close_at(DayState& s,double bid,double ask,int sec,const string& reason,bool target){
    if(s.pos!=0){
        s.realized += open_pnl(s,bid,ask) - COMM_SIDE;
        s.pos=0;
    }
    s.min_liq=min(s.min_liq,s.realized);
    emit_day(s,s.realized,reason,sec,target);
}

void finalize_previous(DayState& s){
    if(!s.active || s.emitted) return;
    // If a weekday had ticks but no 20:00+ tick, flatten on last seen quote.
    if(s.pos!=0) close_at(s,s.last_bid,s.last_ask,s.last_sec,"DAY_END_LAST_TICK",false);
    else emit_day(s,s.realized,"DAY_END_FLAT",s.last_sec,false);
}

bool parse_line(const string& line,int& y,int& mo,int& d,int& sec,double& bid,double& ask){
    if(line.empty() || line[0]!='\"') return false;
    if(line.rfind("\"Exness\"",0)==0) return false;
    size_t c1=line.find(','); if(c1==string::npos) return false;
    size_t c2=line.find(',',c1+1); if(c2==string::npos) return false;
    size_t c3=line.find(',',c2+1); if(c3==string::npos) return false;
    size_t c4=line.find(',',c3+1); if(c4==string::npos) return false;
    string ts=line.substr(c2+1,c3-c2-1);
    if(!ts.empty() && ts.front()=='\"') ts.erase(ts.begin());
    if(!ts.empty() && ts.back()=='\"') ts.pop_back();
    if(ts.size()<19) return false;
    y=stoi(ts.substr(0,4)); mo=stoi(ts.substr(5,2)); d=stoi(ts.substr(8,2));
    int hh=stoi(ts.substr(11,2)), mm=stoi(ts.substr(14,2)), ss=stoi(ts.substr(17,2));
    sec=hh*3600+mm*60+ss;
    bid=strtod(line.c_str()+c3+1,nullptr);
    ask=strtod(line.c_str()+c4+1,nullptr);
    return isfinite(bid)&&isfinite(ask)&&bid>0&&ask>0;
}

int main(){
    ios::sync_with_stdio(false); cin.tie(nullptr);
    emit_header();
    DayState s;
    string line;
    while(getline(cin,line)){
        int y,mo,d,sec; double bid,ask;
        if(!parse_line(line,y,mo,d,sec,bid,ask)) continue;
        int datekey=y*10000+mo*100+d;
        int oldkey=s.y*10000+s.m*100+s.d;
        if(!s.active || datekey!=oldkey){
            finalize_previous(s);
            s=DayState{}; s.y=y; s.m=mo; s.d=d;
            int wd=weekday_mon0(y,mo,d);
            s.active=(wd>=0 && wd<=4);
            s.min_liq=0.0;
        }
        if(!s.active || s.emitted) continue;
        double mid=(bid+ask)*0.5;
        s.last_bid=bid; s.last_ask=ask; s.last_mid=mid; s.last_sec=sec;

        // Session 06:00-20:00 UTC. First tick at/after 20:00 is liquidation tick.
        if(sec < 6*3600) continue;
        if(sec >= 20*3600){
            if(s.pos!=0) close_at(s,bid,ask,sec,"20UTC_FLAT",false);
            else emit_day(s,s.realized,"20UTC_FLAT",sec,false);
            continue;
        }

        if(!s.ref_set){
            s.ref_set=true; s.ref_mid=mid;
            continue;
        }

        if(s.pos==0){
            if(mid >= s.ref_mid + ENTRY_DIST){
                s.pos=1; s.entry_price=ask; s.entry_mid=mid; s.realized-=COMM_SIDE; s.entry_side="BUY";
                s.min_liq=min(s.min_liq,liquidation(s,bid,ask));
            } else if(mid <= s.ref_mid - ENTRY_DIST){
                s.pos=-1; s.entry_price=bid; s.entry_mid=mid; s.realized-=COMM_SIDE; s.entry_side="SELL";
                s.min_liq=min(s.min_liq,liquidation(s,bid,ask));
            }
            continue;
        }

        double liq=liquidation(s,bid,ask);
        s.min_liq=min(s.min_liq,liq);
        if(liq >= TARGET){
            close_at(s,bid,ask,sec,"TARGET",true);
            continue;
        }

        double revdist = (s.reversals < WIDEN_AFTER) ? ENTRY_DIST : WIDE_DIST;
        bool reverse = (s.pos==1 && mid <= s.entry_mid - revdist) ||
                       (s.pos==-1 && mid >= s.entry_mid + revdist);
        if(reverse){
            // close current
            s.realized += open_pnl(s,bid,ask) - COMM_SIDE;
            int old=s.pos;
            // open opposite immediately on same tick
            s.pos=-old;
            s.realized -= COMM_SIDE;
            s.entry_price=(s.pos==1)?ask:bid;
            s.entry_mid=mid;
            s.reversals++;
            s.min_liq=min(s.min_liq,liquidation(s,bid,ask));
        }
    }
    finalize_previous(s);
    return 0;
}

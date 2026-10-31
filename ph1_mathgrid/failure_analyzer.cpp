#include <bits/stdc++.h>
#include <chrono>
using namespace std;
using namespace std::chrono;

static constexpr double GRID=1.0;
static constexpr double RT_COMM=0.07;
static constexpr double DAILY_TARGET=10.0;

bool parse(const string&l,int&date,int&sec,double&bid,double&ask){
    if(l.empty()||l[0]!='\"'||l.rfind("\"Exness\"",0)==0)return false;
    size_t c1=l.find(','),c2=l.find(',',c1+1),c3=l.find(',',c2+1),c4=l.find(',',c3+1);if(c4==string::npos)return false;
    string t=l.substr(c2+1,c3-c2-1);if(!t.empty()&&t.front()=='\"')t.erase(t.begin());if(!t.empty()&&t.back()=='\"')t.pop_back();if(t.size()<19)return false;
    date=stoi(t.substr(0,4))*10000+stoi(t.substr(5,2))*100+stoi(t.substr(8,2));
    sec=stoi(t.substr(11,2))*3600+stoi(t.substr(14,2))*60+stoi(t.substr(17,2));
    bid=strtod(l.c_str()+c3+1,nullptr); ask=strtod(l.c_str()+c4+1,nullptr);
    return bid>0&&ask>=bid;
}
int wd(int date){int y=date/10000,m=(date/100)%100,d=date%100;weekday w{sys_days{year{y}/month{(unsigned)m}/day{(unsigned)d}}};return w.c_encoding();}
long long dayno(int date){int y=date/10000,m=(date/100)%100,d=date%100;return sys_days{year{y}/month{(unsigned)m}/day{(unsigned)d}}.time_since_epoch().count();}
long long abstime(int date,int sec){return dayno(date)*86400LL+sec;}

struct State{
    int date=0,sec=0,eventIndex=0,nextSide=0,wouldSwitch=0;
    int orders=0,posDepth=0,negDepth=0,twoDepth=0,span=0,switches=0;
    double liq=0,worst=0,elapsedHours=0,startRange=0,dailyRealized=0;
};
struct Basket{
    bool active=false; long long id=0; double zero=0; int buys=0,sells=0; double buySum=0,sellSum=0;
    int maxPos=0,minNeg=0; int startDate=0,startSec=0,startSide=0; long long startAbs=0;
    double startRange=0,startBoundary=0,worst=0; int switches=0,lastLevelSide=0,maxOrders=0,maxTwoDepth=0,maxSpan=0;
    vector<State> states;
    int size()const{return buys+sells;}
};
inline double liq(const Basket&b,double bid,double ask){if(!b.active)return 0;return b.buys*bid-b.buySum+b.sellSum-b.sells*ask-RT_COMM*b.size();}

struct Sim{
    Basket b; long long nextId=1; double dailyRealized=0; bool stoppedToday=false;
    long long hourKey=LLONG_MIN; double hHigh=-1e100,hLow=1e100,lastH=0,lastL=0; bool lastHValid=false;
    double rangeH=0,rangeL=0; bool rangeValid=false,armed=false,needInside=false;
    int curDate=0; bool haveDay=false; double lastBid=0,lastAsk=0; int lastSec=0;
};

ofstream epout,stout;
void epHeader(){
    epout<<"basket_id,start_date,start_sec,end_date,end_sec,start_side,start_h1_range,start_boundary,zero,final_pnl,close_reason,duration_hours,orders,max_pos_depth,max_neg_depth,max_two_depth,max_span,switches,worst_liq\n";
}
void stHeader(){
    stout<<"basket_id,event_index,date,sec,next_side,would_switch,orders,pos_depth,neg_depth,two_depth,span,switches,current_liq,worst_liq,elapsed_hours,start_h1_range,daily_realized_before,final_pnl,close_reason\n";
}
void setRangeLatest(Sim&s,bool requireInside){if(s.lastHValid){s.rangeH=s.lastH;s.rangeL=s.lastL;s.rangeValid=true;s.needInside=requireInside;s.armed=!requireInside;}}
void updateWorst(Basket&b,double bid,double ask){if(!b.active)return;double q=liq(b,bid,ask);b.worst=min(b.worst,q);b.maxOrders=max(b.maxOrders,b.size());b.maxTwoDepth=max(b.maxTwoDepth,min(b.maxPos,-b.minNeg));b.maxSpan=max(b.maxSpan,b.maxPos-b.minNeg);}

void emitClose(Sim&s,double bid,double ask,int date,int sec,const string&reason){
    Basket &b=s.b; if(!b.active)return; double q=liq(b,bid,ask); updateWorst(b,bid,ask);
    double dur=(abstime(date,sec)-b.startAbs)/3600.0;
    epout<<b.id<<","<<b.startDate<<","<<b.startSec<<","<<date<<","<<sec<<","<<b.startSide<<","<<fixed<<setprecision(6)<<b.startRange<<","<<b.startBoundary<<","<<b.zero<<","<<q<<","<<reason<<","<<dur<<","<<b.maxOrders<<","<<b.maxPos<<","<<(-b.minNeg)<<","<<b.maxTwoDepth<<","<<b.maxSpan<<","<<b.switches<<","<<b.worst<<"\n";
    for(const auto &x:b.states){
        stout<<b.id<<","<<x.eventIndex<<","<<x.date<<","<<x.sec<<","<<x.nextSide<<","<<x.wouldSwitch<<","<<x.orders<<","<<x.posDepth<<","<<x.negDepth<<","<<x.twoDepth<<","<<x.span<<","<<x.switches<<","<<x.current_liq<<","<<x.worst_liq<<","<<x.elapsedHours<<","<<x.startRange<<","<<x.dailyRealized<<","<<q<<","<<reason<<"\n";
    }
    s.dailyRealized+=q;
    b=Basket(); setRangeLatest(s,true);
    if(s.dailyRealized>=DAILY_TARGET-1e-12)s.stoppedToday=true;
}

void startBasket(Sim&s,int side,double bid,double ask,int date,int sec){
    s.b=Basket(); auto &b=s.b; b.active=true;b.id=s.nextId++;b.startDate=date;b.startSec=sec;b.startAbs=abstime(date,sec);b.startSide=side;
    b.startRange=s.rangeValid?(s.rangeH-s.rangeL):0;b.startBoundary=(side==1?s.rangeH:s.rangeL);b.zero=bid;
    double fill=side==1?ask:bid;if(side==1){b.buys=1;b.buySum=fill;}else{b.sells=1;b.sellSum=fill;}
    b.worst=liq(b,bid,ask);b.maxOrders=1;b.maxTwoDepth=0;b.maxSpan=0;s.armed=false;
}

void recordPreAdd(Sim&s,int side,double bid,double ask,int date,int sec){
    auto &b=s.b;State x;x.date=date;x.sec=sec;x.eventIndex=(int)b.states.size()+1;x.nextSide=side;x.wouldSwitch=(b.lastLevelSide!=0&&b.lastLevelSide!=side);
    x.orders=b.size();x.posDepth=b.maxPos;x.negDepth=-b.minNeg;x.twoDepth=min(x.posDepth,x.negDepth);x.span=x.posDepth+x.negDepth;x.switches=b.switches;
    x.current_liq=liq(b,bid,ask);x.worst_liq=min(b.worst,x.current_liq);x.elapsedHours=(abstime(date,sec)-b.startAbs)/3600.0;x.startRange=b.startRange;x.dailyRealized=s.dailyRealized;
    b.states.push_back(x);
}
void addOrder(Sim&s,int side,double bid,double ask){
    auto &b=s.b;double fill=side==1?ask:bid;if(side==1){b.buys++;b.buySum+=fill;}else{b.sells++;b.sellSum+=fill;}
    if(b.lastLevelSide!=0&&b.lastLevelSide!=side)b.switches++;b.lastLevelSide=side;updateWorst(b,bid,ask);
}

int main(int argc,char**argv){
    ios::sync_with_stdio(false);cin.tie(nullptr);
    string prefix=(argc>1?argv[1]:"out");epout.open(prefix+"_episodes.csv");stout.open(prefix+"_states.csv");epHeader();stHeader();
    Sim s;string line;int date,sec;double bid,ask;
    while(getline(cin,line)){
        if(!parse(line,date,sec,bid,ask))continue;
        if(!s.haveDay){s.haveDay=true;s.curDate=date;s.dailyRealized=0;s.stoppedToday=false;}
        if(date!=s.curDate){
            if(wd(s.curDate)==5&&s.b.active)emitClose(s,s.lastBid,s.lastAsk,s.curDate,s.lastSec,"friday_flat");
            s.curDate=date;s.dailyRealized=0;s.stoppedToday=false;
        }
        s.lastBid=bid;s.lastAsk=ask;s.lastSec=sec;
        long long hk=(long long)date*24+sec/3600;
        if(s.hourKey==LLONG_MIN){s.hourKey=hk;s.hHigh=bid;s.hLow=bid;continue;}
        if(hk!=s.hourKey){
            s.lastH=s.hHigh;s.lastL=s.hLow;s.lastHValid=(s.hHigh>s.hLow);
            if(!s.b.active&&!s.stoppedToday&&wd(date)>=1&&wd(date)<=5)setRangeLatest(s,false);
            s.hourKey=hk;s.hHigh=bid;s.hLow=bid;
        }else{s.hHigh=max(s.hHigh,bid);s.hLow=min(s.hLow,bid);}
        if(s.b.active)updateWorst(s.b,bid,ask);
        int weekdayNow=wd(date);if(weekdayNow==0||weekdayNow==6)continue;
        if(s.stoppedToday)continue;
        if(!s.b.active){
            if(!s.rangeValid)continue;
            if(s.needInside){if(bid<=s.rangeH&&bid>=s.rangeL){s.needInside=false;s.armed=true;}else continue;}
            if(!s.armed)continue;
            if(bid>s.rangeH)startBasket(s,1,bid,ask,date,sec);else if(bid<s.rangeL)startBasket(s,-1,bid,ask,date,sec);
            continue;
        }
        double q=liq(s.b,bid,ask);
        if(s.dailyRealized+q>=DAILY_TARGET-1e-12){emitClose(s,bid,ask,date,sec,"daily_target");continue;}
        bool cp=bid>=s.b.zero+(s.b.maxPos+1)*GRID;
        bool cn=bid<=s.b.zero+(s.b.minNeg-1)*GRID;
        if(cp){
            while(s.b.active&&bid>=s.b.zero+(s.b.maxPos+1)*GRID){
                q=liq(s.b,bid,ask);if(q>0){emitClose(s,bid,ask,date,sec,"cycle_profit");break;}
                recordPreAdd(s,1,bid,ask,date,sec);s.b.maxPos++;addOrder(s,1,bid,ask);
                q=liq(s.b,bid,ask);if(s.dailyRealized+q>=DAILY_TARGET-1e-12){emitClose(s,bid,ask,date,sec,"daily_target");break;}
            }
        }else if(cn){
            while(s.b.active&&bid<=s.b.zero+(s.b.minNeg-1)*GRID){
                q=liq(s.b,bid,ask);if(q>0){emitClose(s,bid,ask,date,sec,"cycle_profit");break;}
                recordPreAdd(s,-1,bid,ask,date,sec);s.b.minNeg--;addOrder(s,-1,bid,ask);
                q=liq(s.b,bid,ask);if(s.dailyRealized+q>=DAILY_TARGET-1e-12){emitClose(s,bid,ask,date,sec,"daily_target");break;}
            }
        }
    }
    if(s.haveDay&&s.b.active)emitClose(s,s.lastBid,s.lastAsk,s.curDate,s.lastSec,"end_data");
    return 0;
}

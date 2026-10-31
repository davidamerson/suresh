#include <bits/stdc++.h>
#include <chrono>
using namespace std;
using namespace std::chrono;

static constexpr double GRID=1.0;
static constexpr double RT_COMM=0.07;
static constexpr double DAILY_TARGET=10.0;
static constexpr double LEVERAGE=2000.0;

bool parseTick(const string&l,int&date,int&sec,double&bid,double&ask){
    if(l.empty()||l[0]!='\"'||l.rfind("\"Exness\"",0)==0)return false;
    size_t c1=l.find(','),c2=l.find(',',c1+1),c3=l.find(',',c2+1),c4=l.find(',',c3+1);
    if(c4==string::npos)return false;
    string t=l.substr(c2+1,c3-c2-1);
    if(!t.empty()&&t.front()=='\"')t.erase(t.begin());
    if(!t.empty()&&t.back()=='\"')t.pop_back();
    if(t.size()<19)return false;
    date=stoi(t.substr(0,4))*10000+stoi(t.substr(5,2))*100+stoi(t.substr(8,2));
    sec=stoi(t.substr(11,2))*3600+stoi(t.substr(14,2))*60+stoi(t.substr(17,2));
    bid=strtod(l.c_str()+c3+1,nullptr); ask=strtod(l.c_str()+c4+1,nullptr);
    return bid>0&&ask>=bid;
}
int weekdayOf(int date){
    int y=date/10000,m=(date/100)%100,d=date%100;
    weekday w{sys_days{year{y}/month{(unsigned)m}/day{(unsigned)d}}};
    return w.c_encoding();
}

struct GuardConfig{
    string name;
    int minTwoDepth;      // trigger once both sides have visited at least this many levels
    double maxLiq;        // trigger only if current liquidation P/L <= maxLiq; +inf means depth-only
};

vector<GuardConfig> configs(){
    const double INF=1e100;
    return {
        {"BASE",999, -INF},
        {"D3",3,INF},{"D4",4,INF},{"D5",5,INF},{"D6",6,INF},{"D7",7,INF},{"D8",8,INF},{"D9",9,INF},{"D10",10,INF},
        {"D3Q20",3,-20},{"D4Q30",4,-30},{"D5Q40",5,-40},{"D6Q50",6,-50},{"D7Q60",7,-60},{"D8Q80",8,-80},{"D9Q100",9,-100},{"D10Q110",10,-110}
    };
}

struct Basket{
    bool active=false;
    double zero=0;
    int buys=0,sells=0;
    double buySum=0,sellSum=0;
    int maxPos=0,minNeg=0;
    int size()const{return buys+sells;}
};
inline double liq(const Basket&b,double bid,double ask){
    if(!b.active)return 0;
    return b.buys*bid-b.buySum+b.sellSum-b.sells*ask-RT_COMM*b.size();
}
inline double marginNow(const Basket&b,double mid){return b.size()*mid/LEVERAGE;}

struct DayStats{
    int date=0;
    double realized=0;
    bool target=false,marginFail=false,accountFail=false;
    int baskets=0,wins=0,fridayCloses=0,orders=0,maxOpen=0,guardTriggers=0;
    double guardRealized=0;
    double minEquity=1e100,maxMargin=0;
};

struct Sim{
    GuardConfig cfg;
    double balance=1000.0;
    bool alive=true;
    Basket b;
    DayStats ds;
    bool stoppedToday=false;
    double rangeH=0,rangeL=0;
    bool rangeValid=false,armed=false,needInside=false;
};

struct GlobalH1{
    long long key=LLONG_MIN;
    double curHigh=-1e100,curLow=1e100;
    double lastHigh=0,lastLow=0;
    bool lastValid=false;
};

void setRangeLatest(Sim&s,const GlobalH1&h,bool requireInside){
    if(h.lastValid){s.rangeH=h.lastHigh;s.rangeL=h.lastLow;s.rangeValid=true;s.needInside=requireInside;s.armed=!requireInside;}
}
void newDay(Sim&s,int date,double bid,double ask){
    s.ds=DayStats(); s.ds.date=date;
    s.ds.minEquity=s.balance+liq(s.b,bid,ask);
    s.stoppedToday=false;
}
void updateRisk(Sim&s,double bid,double ask){
    if(!s.alive)return;
    double eq=s.balance+liq(s.b,bid,ask);
    s.ds.minEquity=min(s.ds.minEquity,eq);
    s.ds.maxOpen=max(s.ds.maxOpen,s.b.size());
    s.ds.maxMargin=max(s.ds.maxMargin,marginNow(s.b,(bid+ask)/2.0));
    if(eq<=0){s.alive=false;s.ds.accountFail=true;s.balance=0;}
}
bool canOpenOne(const Sim&s,double bid,double ask){
    double eq=s.balance+liq(s.b,bid,ask);
    double newMargin=(s.b.size()+1)*((bid+ask)/2.0)/LEVERAGE;
    return eq>=newMargin;
}
void closeBasket(Sim&s,const GlobalH1&h,double bid,double ask,bool win,bool friday,bool guard){
    double q=liq(s.b,bid,ask);
    s.balance+=q; s.ds.realized+=q;
    if(win)s.ds.wins++;
    if(friday)s.ds.fridayCloses++;
    if(guard){s.ds.guardTriggers++;s.ds.guardRealized+=q;}
    s.b=Basket();
    setRangeLatest(s,h,true);
    if(s.balance<=0){s.balance=0;s.alive=false;s.ds.accountFail=true;}
    if(s.ds.realized>=DAILY_TARGET-1e-12){s.ds.target=true;s.stoppedToday=true;}
}
void startBasket(Sim&s,int side,double bid,double ask){
    if(!canOpenOne(s,bid,ask)){s.ds.marginFail=true;s.alive=false;return;}
    s.b=Basket();s.b.active=true;s.b.zero=bid;
    double fill=side==1?ask:bid;
    if(side==1){s.b.buys=1;s.b.buySum=fill;}else{s.b.sells=1;s.b.sellSum=fill;}
    s.ds.baskets++;s.ds.orders++;s.armed=false;
    updateRisk(s,bid,ask);
}
void addOrder(Sim&s,int side,double bid,double ask){
    if(!canOpenOne(s,bid,ask)){s.ds.marginFail=true;s.alive=false;return;}
    double fill=side==1?ask:bid;
    if(side==1){s.b.buys++;s.b.buySum+=fill;}else{s.b.sells++;s.b.sellSum+=fill;}
    s.ds.orders++;
    updateRisk(s,bid,ask);
}
bool guardHit(const Sim&s,double q){
    if(s.cfg.name=="BASE")return false;
    int two=min(s.b.maxPos,-s.b.minNeg);
    if(two<s.cfg.minTwoDepth)return false;
    if(s.cfg.maxLiq>1e50)return true;
    return q<=s.cfg.maxLiq;
}

void processTick(Sim&s,const GlobalH1&h,int date,double bid,double ask){
    if(!s.alive)return;
    updateRisk(s,bid,ask); if(!s.alive)return;
    int w=weekdayOf(date);
    if(w==0||w==6)return;
    if(s.stoppedToday)return;

    if(!s.b.active){
        if(!s.rangeValid)return;
        if(s.needInside){
            if(bid<=s.rangeH&&bid>=s.rangeL){s.needInside=false;s.armed=true;}else return;
        }
        if(!s.armed)return;
        if(bid>s.rangeH)startBasket(s,+1,bid,ask);
        else if(bid<s.rangeL)startBasket(s,-1,bid,ask);
        return;
    }

    double q=liq(s.b,bid,ask);
    if(s.ds.realized+q>=DAILY_TARGET-1e-12){closeBasket(s,h,bid,ask,false,false,false);return;}

    bool cp=bid>=s.b.zero+(s.b.maxPos+1)*GRID;
    bool cn=bid<=s.b.zero+(s.b.minNeg-1)*GRID;
    if(cp){
        while(s.alive&&s.b.active&&bid>=s.b.zero+(s.b.maxPos+1)*GRID){
            q=liq(s.b,bid,ask);
            if(q>0){closeBasket(s,h,bid,ask,true,false,false);break;}
            if(guardHit(s,q)){closeBasket(s,h,bid,ask,false,false,true);break;}
            s.b.maxPos++; addOrder(s,+1,bid,ask); if(!s.alive)break;
            q=liq(s.b,bid,ask);
            if(s.ds.realized+q>=DAILY_TARGET-1e-12){closeBasket(s,h,bid,ask,false,false,false);break;}
        }
    }else if(cn){
        while(s.alive&&s.b.active&&bid<=s.b.zero+(s.b.minNeg-1)*GRID){
            q=liq(s.b,bid,ask);
            if(q>0){closeBasket(s,h,bid,ask,true,false,false);break;}
            if(guardHit(s,q)){closeBasket(s,h,bid,ask,false,false,true);break;}
            s.b.minNeg--; addOrder(s,-1,bid,ask); if(!s.alive)break;
            q=liq(s.b,bid,ask);
            if(s.ds.realized+q>=DAILY_TARGET-1e-12){closeBasket(s,h,bid,ask,false,false,false);break;}
        }
    }
}

void selftest(){
    vector<pair<double,int>>v={{1,1},{2,4},{2,4},{2,7},{2,7}};
    cout<<"name,net\n";
    for(int i=0;i<5;i++)cout<<"scenario"<<i+1<<","<<fixed<<setprecision(2)<<v[i].first-RT_COMM*v[i].second<<"\n";
}

int main(int argc,char**argv){
    ios::sync_with_stdio(false);cin.tie(nullptr);
    if(argc>1&&string(argv[1])=="--selftest"){selftest();return 0;}
    auto cs=configs(); vector<Sim> sims; sims.reserve(cs.size());
    for(auto &c:cs){Sim s;s.cfg=c;sims.push_back(s);}
    cout<<"config,date,realized_pnl,target_hit,margin_fail,account_fail,baskets,cycle_wins,friday_closes,total_orders,max_open,guard_triggers,guard_realized,min_equity,max_margin_1_2000,balance_end\n";

    GlobalH1 h; string line; int date,sec;double bid,ask; bool haveDay=false;int curDate=0;double lastBid=0,lastAsk=0;
    while(getline(cin,line)){
        if(!parseTick(line,date,sec,bid,ask))continue;
        if(!haveDay){haveDay=true;curDate=date;lastBid=bid;lastAsk=ask;for(auto &s:sims)newDay(s,date,bid,ask);}
        if(date!=curDate){
            for(auto &s:sims){
                if(s.alive&&weekdayOf(curDate)==5&&s.b.active)closeBasket(s,h,lastBid,lastAsk,false,true,false);
                auto &d=s.ds;
                cout<<s.cfg.name<<","<<d.date<<","<<fixed<<setprecision(6)<<d.realized<<","<<(d.target?1:0)<<","<<(d.marginFail?1:0)<<","<<(d.accountFail?1:0)<<","<<d.baskets<<","<<d.wins<<","<<d.fridayCloses<<","<<d.orders<<","<<d.maxOpen<<","<<d.guardTriggers<<","<<d.guardRealized<<","<<d.minEquity<<","<<d.maxMargin<<","<<s.balance<<"\n";
                if(s.alive)newDay(s,date,bid,ask);
                else {s.ds=DayStats();s.ds.date=date;s.ds.minEquity=s.balance;}
            }
            curDate=date;
        }
        lastBid=bid;lastAsk=ask;

        long long hk=(long long)date*24+sec/3600;
        bool hourChanged=false;
        if(h.key==LLONG_MIN){h.key=hk;h.curHigh=bid;h.curLow=bid;}
        else if(hk!=h.key){
            h.lastHigh=h.curHigh;h.lastLow=h.curLow;h.lastValid=(h.curHigh>h.curLow);
            h.key=hk;h.curHigh=bid;h.curLow=bid;hourChanged=true;
        }else{h.curHigh=max(h.curHigh,bid);h.curLow=min(h.curLow,bid);}
        if(hourChanged&&weekdayOf(date)>=1&&weekdayOf(date)<=5){
            for(auto &s:sims)if(s.alive&&!s.b.active&&!s.stoppedToday)setRangeLatest(s,h,false);
        }
        for(auto &s:sims)processTick(s,h,date,bid,ask);
    }
    if(haveDay){
        for(auto &s:sims){
            if(s.alive&&weekdayOf(curDate)==5&&s.b.active)closeBasket(s,h,lastBid,lastAsk,false,true,false);
            auto &d=s.ds;
            cout<<s.cfg.name<<","<<d.date<<","<<fixed<<setprecision(6)<<d.realized<<","<<(d.target?1:0)<<","<<(d.marginFail?1:0)<<","<<(d.accountFail?1:0)<<","<<d.baskets<<","<<d.wins<<","<<d.fridayCloses<<","<<d.orders<<","<<d.maxOpen<<","<<d.guardTriggers<<","<<d.guardRealized<<","<<d.minEquity<<","<<d.maxMargin<<","<<s.balance<<"\n";
        }
    }
    return 0;
}

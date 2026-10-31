#include <bits/stdc++.h>
using namespace std;

static constexpr double GRID = 1.0;
static constexpr double RT_COMM_PER_001 = 0.07; // $0.035/side * 2
static constexpr double DAILY_TARGET = 10.0;
static constexpr double EMERGENCY = -100.0;
static constexpr double LEVERAGE = 2000.0;

struct Pos { int side; double entry; };
struct Basket {
    bool active=false;
    int firstSide=0;
    double zero=0;
    vector<Pos> p;
    int maxPosLevel=0;
    int minNegLevel=0;
    double minLiq=0;
};
struct Day {
    int date=0;
    double bank=0;
    bool stopped=false;
    bool targetHit=false;
    bool emergency=false;
    int baskets=0;
    int cycleWins=0;
    int forcedCloses=0;
    int totalOrders=0;
    int maxOpen=0;
    double worstDelta=0;
    double maxMargin=0;
    Basket b;
    bool rangeValid=false;
    double rangeHigh=0, rangeLow=0;
    bool armed=false;
    bool needInside=false;
    int hourKey=-1;
    double hHigh=-1e100, hLow=1e100;
};

bool parse(const string& l, int& date, int& sec, double& bid, double& ask) {
    if(l.empty() || l[0] != '"' || l.rfind("\"Exness\"",0)==0) return false;
    size_t c1=l.find(','), c2=l.find(',',c1+1), c3=l.find(',',c2+1), c4=l.find(',',c3+1);
    if(c4==string::npos) return false;
    string t=l.substr(c2+1,c3-c2-1);
    if(!t.empty() && t.front()=='"') t.erase(t.begin());
    if(!t.empty() && t.back()=='"') t.pop_back();
    if(t.size()<19) return false;
    date=stoi(t.substr(0,4))*10000+stoi(t.substr(5,2))*100+stoi(t.substr(8,2));
    sec=stoi(t.substr(11,2))*3600+stoi(t.substr(14,2))*60+stoi(t.substr(17,2));
    bid=strtod(l.c_str()+c3+1,nullptr);
    ask=strtod(l.c_str()+c4+1,nullptr);
    return bid>0 && ask>=bid;
}

double liq(const Basket& b, double bid, double ask) {
    if(!b.active) return 0;
    double x=0;
    for(const auto &q:b.p) x += q.side==1 ? (bid-q.entry) : (q.entry-ask);
    x -= RT_COMM_PER_001 * b.p.size();
    return x;
}

double marginNow(const Basket& b, double mid) {
    return b.p.size() * mid / LEVERAGE; // 0.01 lot XAU = 1 oz
}

void resetDay(Day& d, int date) {
    d=Day(); d.date=date;
}

void closeBasket(Day& d, double bid, double ask, bool cycleWin, bool forced, bool emergency) {
    double q=liq(d.b,bid,ask);
    d.bank += q;
    d.worstDelta=min(d.worstDelta,d.bank);
    if(cycleWin) d.cycleWins++;
    if(forced) d.forcedCloses++;
    if(emergency){d.emergency=true; d.stopped=true;}
    d.b=Basket();
    d.needInside=true;
    d.armed=false;
    if(d.bank>=DAILY_TARGET-1e-12){d.targetHit=true; d.stopped=true;}
}

void startBasket(Day& d, int side, double bid, double ask, bool fillZero) {
    d.b=Basket(); d.b.active=true; d.b.firstSide=side;
    double fill = side==1 ? ask : bid;
    d.b.zero = fillZero ? fill : bid; // chart-zero uses Bid breakout price
    d.b.p.push_back({side,fill});
    d.b.maxPosLevel=0; d.b.minNegLevel=0;
    d.b.minLiq=liq(d.b,bid,ask);
    d.baskets++; d.totalOrders++; d.maxOpen=max(d.maxOpen,1);
    d.maxMargin=max(d.maxMargin,marginNow(d.b,(bid+ask)/2));
    d.worstDelta=min(d.worstDelta,d.bank+d.b.minLiq);
    d.armed=false;
}

void addOrder(Day& d, int side, double bid, double ask) {
    double fill=side==1?ask:bid;
    d.b.p.push_back({side,fill});
    d.totalOrders++; d.maxOpen=max(d.maxOpen,(int)d.b.p.size());
    double q=liq(d.b,bid,ask);
    d.b.minLiq=min(d.b.minLiq,q);
    d.worstDelta=min(d.worstDelta,d.bank+q);
    d.maxMargin=max(d.maxMargin,marginNow(d.b,(bid+ask)/2));
}

void finalizeDay(Day& d, double lastBid, double lastAsk, bool haveLast) {
    if(haveLast && d.b.active) closeBasket(d,lastBid,lastAsk,false,true,false);
}

void printHeader(){
    cout<<"date,day_pnl,target_hit,emergency,baskets,cycle_wins,forced_closes,total_orders,max_open,worst_day_delta,max_margin_1_2000\n";
}
void printDay(const Day& d){
    cout<<d.date<<","<<fixed<<setprecision(6)<<d.bank<<","<<(d.targetHit?1:0)<<","<<(d.emergency?1:0)<<","<<d.baskets<<","<<d.cycleWins<<","<<d.forcedCloses<<","<<d.totalOrders<<","<<d.maxOpen<<","<<d.worstDelta<<","<<d.maxMargin<<"\n";
}

void selftest(){
    vector<pair<string,pair<double,int>>> v={
        {"scenario1",{1.0,1}},
        {"scenario2",{2.0,4}},
        {"scenario3",{2.0,4}},
        {"scenario4",{2.0,7}},
        {"scenario5",{2.0,7}}
    };
    cout<<"name,gross,orders,commission,net,expected\n";
    vector<double> exp={0.93,1.72,1.72,1.51,1.51};
    for(size_t i=0;i<v.size();++i){
        double gross=v[i].second.first; int n=v[i].second.second;
        double comm=n*RT_COMM_PER_001, net=gross-comm;
        cout<<v[i].first<<","<<gross<<","<<n<<","<<comm<<","<<net<<","<<exp[i]<<"\n";
    }
}

int main(int argc,char**argv){
    ios::sync_with_stdio(false); cin.tie(nullptr);
    if(argc>=2 && string(argv[1])=="--selftest"){selftest();return 0;}
    bool fillZero = (argc>=2 && string(argv[1])=="fillzero");
    printHeader();
    Day d; bool haveDay=false, haveLast=false; double lastBid=0,lastAsk=0; int lastDate=0;
    string line;
    while(getline(cin,line)){
        int date,sec; double bid,ask;
        if(!parse(line,date,sec,bid,ask)) continue;
        if(!haveDay || date!=d.date){
            if(haveDay){ finalizeDay(d,lastBid,lastAsk,haveLast); printDay(d); }
            resetDay(d,date); haveDay=true; haveLast=false;
        }
        haveLast=true; lastBid=bid; lastAsk=ask; lastDate=date;
        int hk=sec/3600;
        if(d.hourKey<0){ d.hourKey=hk; d.hHigh=bid; d.hLow=bid; continue; }
        if(hk!=d.hourKey){
            // Last completed H1 candle becomes active reference only if flat.
            if(!d.b.active && !d.stopped && d.hHigh>d.hLow){
                d.rangeHigh=d.hHigh; d.rangeLow=d.hLow; d.rangeValid=true; d.armed=true; d.needInside=false;
            }
            d.hourKey=hk; d.hHigh=bid; d.hLow=bid;
        } else {
            d.hHigh=max(d.hHigh,bid); d.hLow=min(d.hLow,bid);
        }
        if(d.stopped) continue;

        if(!d.b.active){
            if(!d.rangeValid) continue;
            if(d.needInside){
                if(bid<=d.rangeHigh && bid>=d.rangeLow){ d.needInside=false; d.armed=true; }
                else continue;
            }
            if(!d.armed) continue;
            if(bid>d.rangeHigh){ startBasket(d,+1,bid,ask,fillZero); }
            else if(bid<d.rangeLow){ startBasket(d,-1,bid,ask,fillZero); }
            continue;
        }

        double q=liq(d.b,bid,ask);
        d.b.minLiq=min(d.b.minLiq,q);
        d.worstDelta=min(d.worstDelta,d.bank+q);
        d.maxMargin=max(d.maxMargin,marginNow(d.b,(bid+ask)/2));

        // Overall daily target can close mid-grid.
        if(d.bank+q>=DAILY_TARGET-1e-12){ closeBasket(d,bid,ask,false,false,false); continue; }
        if(q<=EMERGENCY){ closeBasket(d,bid,ask,false,false,true); continue; }

        // Original Scenario 1-5 rule: only when a NEW virgin grid level is reached,
        // first test whether closing the whole basket is net-positive. If yes, close;
        // otherwise place the new 0.01 order at that virgin level.
        bool crossedPos = bid >= d.b.zero + (d.b.maxPosLevel+1)*GRID;
        bool crossedNeg = bid <= d.b.zero + (d.b.minNegLevel-1)*GRID;
        if(crossedPos){
            while(bid >= d.b.zero + (d.b.maxPosLevel+1)*GRID){
                q=liq(d.b,bid,ask);
                if(q>0){ closeBasket(d,bid,ask,true,false,false); break; }
                d.b.maxPosLevel++;
                addOrder(d,+1,bid,ask);
                q=liq(d.b,bid,ask);
                if(d.bank+q>=DAILY_TARGET-1e-12){ closeBasket(d,bid,ask,false,false,false); break; }
                if(q<=EMERGENCY){ closeBasket(d,bid,ask,false,false,true); break; }
            }
        } else if(crossedNeg){
            while(bid <= d.b.zero + (d.b.minNegLevel-1)*GRID){
                q=liq(d.b,bid,ask);
                if(q>0){ closeBasket(d,bid,ask,true,false,false); break; }
                d.b.minNegLevel--;
                addOrder(d,-1,bid,ask);
                q=liq(d.b,bid,ask);
                if(d.bank+q>=DAILY_TARGET-1e-12){ closeBasket(d,bid,ask,false,false,false); break; }
                if(q<=EMERGENCY){ closeBasket(d,bid,ask,false,false,true); break; }
            }
        }
    }
    if(haveDay){ finalizeDay(d,lastBid,lastAsk,haveLast); printDay(d); }
    return 0;
}

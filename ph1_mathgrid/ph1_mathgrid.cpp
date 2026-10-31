#include <bits/stdc++.h>
using namespace std;

static constexpr double GRID = 1.0;
static constexpr double RT_COMM_PER_001 = 0.07;
static constexpr double DAILY_TARGET = 10.0;
static constexpr double EMERGENCY = -100.0;
static constexpr double LEVERAGE = 2000.0;

struct Basket {
    bool active=false;
    int firstSide=0;
    double zero=0;
    int buys=0,sells=0;
    double buyEntrySum=0,sellEntrySum=0;
    int maxPosLevel=0,minNegLevel=0;
    double minLiq=0;
    int size() const { return buys+sells; }
};
struct Day {
    int date=0;
    double bank=0;
    bool stopped=false,targetHit=false,emergency=false;
    int baskets=0,cycleWins=0,forcedCloses=0,totalOrders=0,maxOpen=0;
    double worstDelta=0,maxMargin=0;
    Basket b;
    bool rangeValid=false;
    double rangeHigh=0,rangeLow=0;
    bool armed=false,needInside=false;
    int hourKey=-1;
    double hHigh=-1e100,hLow=1e100;
};

bool parse(const string& l,int& date,int& sec,double& bid,double& ask){
    if(l.empty()||l[0]!='"'||l.rfind("\"Exness\"",0)==0) return false;
    size_t c1=l.find(','),c2=l.find(',',c1+1),c3=l.find(',',c2+1),c4=l.find(',',c3+1);
    if(c4==string::npos) return false;
    string t=l.substr(c2+1,c3-c2-1);
    if(!t.empty()&&t.front()=='"') t.erase(t.begin());
    if(!t.empty()&&t.back()=='"') t.pop_back();
    if(t.size()<19) return false;
    date=stoi(t.substr(0,4))*10000+stoi(t.substr(5,2))*100+stoi(t.substr(8,2));
    sec=stoi(t.substr(11,2))*3600+stoi(t.substr(14,2))*60+stoi(t.substr(17,2));
    bid=strtod(l.c_str()+c3+1,nullptr); ask=strtod(l.c_str()+c4+1,nullptr);
    return bid>0&&ask>=bid;
}
inline double liq(const Basket& b,double bid,double ask){
    if(!b.active) return 0;
    double pnl=b.buys*bid-b.buyEntrySum + b.sellEntrySum-b.sells*ask;
    return pnl-RT_COMM_PER_001*b.size();
}
inline double marginNow(const Basket& b,double mid){return b.size()*mid/LEVERAGE;}
void resetDay(Day& d,int date){d=Day();d.date=date;}

void closeBasket(Day& d,double bid,double ask,bool cycleWin,bool forced,bool emergency){
    double q=liq(d.b,bid,ask); d.bank+=q; d.worstDelta=min(d.worstDelta,d.bank);
    if(cycleWin)d.cycleWins++; if(forced)d.forcedCloses++;
    if(emergency){d.emergency=true;d.stopped=true;}
    d.b=Basket(); d.needInside=true; d.armed=false;
    if(d.bank>=DAILY_TARGET-1e-12){d.targetHit=true;d.stopped=true;}
}
void startBasket(Day& d,int side,double bid,double ask,bool fillZero){
    d.b=Basket();d.b.active=true;d.b.firstSide=side;
    double fill=side==1?ask:bid; d.b.zero=fillZero?fill:bid;
    if(side==1){d.b.buys=1;d.b.buyEntrySum=fill;}else{d.b.sells=1;d.b.sellEntrySum=fill;}
    d.b.minLiq=liq(d.b,bid,ask); d.baskets++;d.totalOrders++;d.maxOpen=max(d.maxOpen,1);
    d.maxMargin=max(d.maxMargin,marginNow(d.b,(bid+ask)/2));
    d.worstDelta=min(d.worstDelta,d.bank+d.b.minLiq);d.armed=false;
}
void addOrder(Day& d,int side,double bid,double ask){
    double fill=side==1?ask:bid;
    if(side==1){d.b.buys++;d.b.buyEntrySum+=fill;}else{d.b.sells++;d.b.sellEntrySum+=fill;}
    d.totalOrders++;d.maxOpen=max(d.maxOpen,d.b.size());
    double q=liq(d.b,bid,ask);d.b.minLiq=min(d.b.minLiq,q);d.worstDelta=min(d.worstDelta,d.bank+q);
    d.maxMargin=max(d.maxMargin,marginNow(d.b,(bid+ask)/2));
}
void finalizeDay(Day& d,double bid,double ask,bool haveLast){if(haveLast&&d.b.active)closeBasket(d,bid,ask,false,true,false);}
void printHeader(){cout<<"date,day_pnl,target_hit,emergency,baskets,cycle_wins,forced_closes,total_orders,max_open,worst_day_delta,max_margin_1_2000\n";}
void printDay(const Day& d){cout<<d.date<<","<<fixed<<setprecision(6)<<d.bank<<","<<(d.targetHit?1:0)<<","<<(d.emergency?1:0)<<","<<d.baskets<<","<<d.cycleWins<<","<<d.forcedCloses<<","<<d.totalOrders<<","<<d.maxOpen<<","<<d.worstDelta<<","<<d.maxMargin<<"\n";}
void selftest(){
    vector<pair<double,int>> v={{1,1},{2,4},{2,4},{2,7},{2,7}};vector<double> e={.93,1.72,1.72,1.51,1.51};
    cout<<"name,gross,orders,commission,net,expected\n";
    for(int i=0;i<5;i++){double c=v[i].second*RT_COMM_PER_001,n=v[i].first-c;cout<<"scenario"<<i+1<<","<<v[i].first<<","<<v[i].second<<","<<c<<","<<n<<","<<e[i]<<"\n";}
}
int main(int argc,char**argv){
    ios::sync_with_stdio(false);cin.tie(nullptr);
    if(argc>=2&&string(argv[1])=="--selftest"){selftest();return 0;}
    bool fillZero=(argc>=2&&string(argv[1])=="fillzero");printHeader();
    Day d;bool haveDay=false,haveLast=false;double lastBid=0,lastAsk=0;string line;
    while(getline(cin,line)){
        int date,sec;double bid,ask;if(!parse(line,date,sec,bid,ask))continue;
        if(!haveDay||date!=d.date){if(haveDay){finalizeDay(d,lastBid,lastAsk,haveLast);printDay(d);}resetDay(d,date);haveDay=true;haveLast=false;}
        haveLast=true;lastBid=bid;lastAsk=ask;int hk=sec/3600;
        if(d.hourKey<0){d.hourKey=hk;d.hHigh=bid;d.hLow=bid;continue;}
        if(hk!=d.hourKey){if(!d.b.active&&!d.stopped&&d.hHigh>d.hLow){d.rangeHigh=d.hHigh;d.rangeLow=d.hLow;d.rangeValid=true;d.armed=true;d.needInside=false;}d.hourKey=hk;d.hHigh=bid;d.hLow=bid;}
        else{d.hHigh=max(d.hHigh,bid);d.hLow=min(d.hLow,bid);}
        if(d.stopped)continue;
        if(!d.b.active){
            if(!d.rangeValid)continue;
            if(d.needInside){if(bid<=d.rangeHigh&&bid>=d.rangeLow){d.needInside=false;d.armed=true;}else continue;}
            if(!d.armed)continue;
            if(bid>d.rangeHigh)startBasket(d,1,bid,ask,fillZero);else if(bid<d.rangeLow)startBasket(d,-1,bid,ask,fillZero);
            continue;
        }
        double q=liq(d.b,bid,ask);d.b.minLiq=min(d.b.minLiq,q);d.worstDelta=min(d.worstDelta,d.bank+q);d.maxMargin=max(d.maxMargin,marginNow(d.b,(bid+ask)/2));
        if(d.bank+q>=DAILY_TARGET-1e-12){closeBasket(d,bid,ask,false,false,false);continue;}
        if(q<=EMERGENCY){closeBasket(d,bid,ask,false,false,true);continue;}
        bool cp=bid>=d.b.zero+(d.b.maxPosLevel+1)*GRID;
        bool cn=bid<=d.b.zero+(d.b.minNegLevel-1)*GRID;
        if(cp){
            while(bid>=d.b.zero+(d.b.maxPosLevel+1)*GRID){
                q=liq(d.b,bid,ask);if(q>0){closeBasket(d,bid,ask,true,false,false);break;}
                d.b.maxPosLevel++;addOrder(d,1,bid,ask);q=liq(d.b,bid,ask);
                if(d.bank+q>=DAILY_TARGET-1e-12){closeBasket(d,bid,ask,false,false,false);break;}
                if(q<=EMERGENCY){closeBasket(d,bid,ask,false,false,true);break;}
            }
        }else if(cn){
            while(bid<=d.b.zero+(d.b.minNegLevel-1)*GRID){
                q=liq(d.b,bid,ask);if(q>0){closeBasket(d,bid,ask,true,false,false);break;}
                d.b.minNegLevel--;addOrder(d,-1,bid,ask);q=liq(d.b,bid,ask);
                if(d.bank+q>=DAILY_TARGET-1e-12){closeBasket(d,bid,ask,false,false,false);break;}
                if(q<=EMERGENCY){closeBasket(d,bid,ask,false,false,true);break;}
            }
        }
    }
    if(haveDay){finalizeDay(d,lastBid,lastAsk,haveLast);printDay(d);}return 0;
}

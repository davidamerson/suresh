#include <bits/stdc++.h>
#include <chrono>
using namespace std;
using namespace std::chrono;

static constexpr double GRID=1.0;
static constexpr double RT_COMM=0.07;
static constexpr double DAILY_TARGET=10.0;
static constexpr double LEVERAGE=2000.0;

struct Basket{
    bool active=false; double zero=0; int buys=0,sells=0; double buySum=0,sellSum=0;
    int maxPosLevel=0,minNegLevel=0; int size()const{return buys+sells;}
};
struct DayStats{
    int date=0; double realized=0; bool target=false,marginFail=false,accountFail=false;
    int baskets=0,wins=0,fridayCloses=0,orders=0,maxOpen=0; double minEquity=1e100,maxMargin=0;
};

bool parse(const string&l,int&date,int&sec,double&bid,double&ask){
    if(l.empty()||l[0]!='\"'||l.rfind("\"Exness\"",0)==0)return false;
    size_t c1=l.find(','),c2=l.find(',',c1+1),c3=l.find(',',c2+1),c4=l.find(',',c3+1);if(c4==string::npos)return false;
    string t=l.substr(c2+1,c3-c2-1);if(!t.empty()&&t.front()=='\"')t.erase(t.begin());if(!t.empty()&&t.back()=='\"')t.pop_back();if(t.size()<19)return false;
    date=stoi(t.substr(0,4))*10000+stoi(t.substr(5,2))*100+stoi(t.substr(8,2));sec=stoi(t.substr(11,2))*3600+stoi(t.substr(14,2))*60+stoi(t.substr(17,2));
    bid=strtod(l.c_str()+c3+1,nullptr);ask=strtod(l.c_str()+c4+1,nullptr);return bid>0&&ask>=bid;
}
int wd(int date){int y=date/10000,m=(date/100)%100,d=date%100;weekday w{sys_days{year{y}/month{(unsigned)m}/day{(unsigned)d}}};return w.c_encoding();}
inline double liq(const Basket&b,double bid,double ask){if(!b.active)return 0;return b.buys*bid-b.buySum+b.sellSum-b.sells*ask-RT_COMM*b.size();}
inline double margin(const Basket&b,double mid){return b.size()*mid/LEVERAGE;}

struct Sim{
    double balance=1000.0; bool alive=true; Basket b; DayStats ds;
    bool stoppedToday=false;
    long long hourKey=LLONG_MIN; double hHigh=-1e100,hLow=1e100,lastH=0,lastL=0; bool lastHValid=false;
    double rangeH=0,rangeL=0; bool rangeValid=false,armed=false,needInside=false;
    double lastBid=0,lastAsk=0; int lastDate=0; bool haveLast=false;
};

void printHeader(){cout<<"date,realized_pnl,target_hit,margin_fail,account_fail,baskets,cycle_wins,friday_closes,total_orders,max_open,min_equity,max_margin_1_2000,balance_end\n";}
void printDay(const Sim&s){const auto&d=s.ds;cout<<d.date<<","<<fixed<<setprecision(6)<<d.realized<<","<<(d.target?1:0)<<","<<(d.marginFail?1:0)<<","<<(d.accountFail?1:0)<<","<<d.baskets<<","<<d.wins<<","<<d.fridayCloses<<","<<d.orders<<","<<d.maxOpen<<","<<d.minEquity<<","<<d.maxMargin<<","<<s.balance<<"\n";}
void newDay(Sim&s,int date){s.ds=DayStats();s.ds.date=date;s.ds.minEquity=s.balance+(s.b.active?liq(s.b,s.lastBid,s.lastAsk):0);s.stoppedToday=false;}
void updateRisk(Sim&s,double bid,double ask){if(!s.alive)return;double eq=s.balance+liq(s.b,bid,ask);s.ds.minEquity=min(s.ds.minEquity,eq);s.ds.maxOpen=max(s.ds.maxOpen,s.b.size());s.ds.maxMargin=max(s.ds.maxMargin,margin(s.b,(bid+ask)/2));if(eq<=0){s.alive=false;s.ds.accountFail=true;s.balance=0;}}
bool canOpenOne(const Sim&s,double bid,double ask){double eq=s.balance+liq(s.b,bid,ask);double newMargin=(s.b.size()+1)*((bid+ask)/2)/LEVERAGE;return eq>=newMargin;}
void setRangeLatest(Sim&s,bool requireInside){if(s.lastHValid){s.rangeH=s.lastH;s.rangeL=s.lastL;s.rangeValid=true;s.needInside=requireInside;s.armed=!requireInside;}}
void closeBasket(Sim&s,double bid,double ask,bool win,bool fri){double q=liq(s.b,bid,ask);s.balance+=q;s.ds.realized+=q;if(win)s.ds.wins++;if(fri)s.ds.fridayCloses++;s.b=Basket();setRangeLatest(s,true);if(s.balance<=0){s.balance=0;s.alive=false;s.ds.accountFail=true;}if(s.ds.realized>=DAILY_TARGET-1e-12){s.ds.target=true;s.stoppedToday=true;}}
void startBasket(Sim&s,int side,double bid,double ask){if(!canOpenOne(s,bid,ask)){s.ds.marginFail=true;s.alive=false;return;}s.b=Basket();s.b.active=true;s.b.zero=bid;double fill=side==1?ask:bid;if(side==1){s.b.buys=1;s.b.buySum=fill;}else{s.b.sells=1;s.b.sellSum=fill;}s.ds.baskets++;s.ds.orders++;s.armed=false;updateRisk(s,bid,ask);}
void addOrder(Sim&s,int side,double bid,double ask){if(!canOpenOne(s,bid,ask)){s.ds.marginFail=true;s.alive=false;return;}double fill=side==1?ask:bid;if(side==1){s.b.buys++;s.b.buySum+=fill;}else{s.b.sells++;s.b.sellSum+=fill;}s.ds.orders++;updateRisk(s,bid,ask);}

void selftest(){vector<pair<double,int>>v={{1,1},{2,4},{2,4},{2,7},{2,7}};cout<<"name,net\n";for(int i=0;i<5;i++)cout<<"scenario"<<i+1<<","<<v[i].first-RT_COMM*v[i].second<<"\n";}

int main(int argc,char**argv){ios::sync_with_stdio(false);cin.tie(nullptr);if(argc>1&&string(argv[1])=="--selftest"){selftest();return 0;}printHeader();Sim s;string line;bool haveDay=false;
    while(getline(cin,line)){
        int date,sec;double bid,ask;if(!parse(line,date,sec,bid,ask))continue;
        if(!haveDay){s.lastBid=bid;s.lastAsk=ask;s.lastDate=date;s.haveLast=true;newDay(s,date);haveDay=true;}
        if(date!=s.ds.date){
            // Friday is the only mandatory flat boundary; no weekend carry.
            if(s.alive&&wd(s.ds.date)==5&&s.b.active){closeBasket(s,s.lastBid,s.lastAsk,false,true);}
            printDay(s);
            if(!s.alive) return 0;
            newDay(s,date);
        }
        s.lastBid=bid;s.lastAsk=ask;s.lastDate=date;s.haveLast=true;
        long long hk=(long long)date*24 + sec/3600;
        if(s.hourKey==LLONG_MIN){s.hourKey=hk;s.hHigh=bid;s.hLow=bid;updateRisk(s,bid,ask);continue;}
        if(hk!=s.hourKey){
            s.lastH=s.hHigh;s.lastL=s.hLow;s.lastHValid=(s.hHigh>s.hLow);
            if(!s.b.active&&!s.stoppedToday&&wd(date)>=1&&wd(date)<=5)setRangeLatest(s,false);
            s.hourKey=hk;s.hHigh=bid;s.hLow=bid;
        }else{s.hHigh=max(s.hHigh,bid);s.hLow=min(s.hLow,bid);}
        updateRisk(s,bid,ask);if(!s.alive){printDay(s);return 0;}
        int weekdayNow=wd(date);if(weekdayNow==0||weekdayNow==6)continue; // no weekend entries
        if(s.stoppedToday)continue;
        if(!s.b.active){
            if(!s.rangeValid)continue;
            if(s.needInside){if(bid<=s.rangeH&&bid>=s.rangeL){s.needInside=false;s.armed=true;}else continue;}
            if(!s.armed)continue;
            if(bid>s.rangeH)startBasket(s,1,bid,ask);else if(bid<s.rangeL)startBasket(s,-1,bid,ask);
            if(!s.alive){printDay(s);return 0;}continue;
        }
        double q=liq(s.b,bid,ask);
        // Daily overall target can liquidate the current basket at any tick.
        if(s.ds.realized+q>=DAILY_TARGET-1e-12){closeBasket(s,bid,ask,false,false);continue;}
        bool cp=bid>=s.b.zero+(s.b.maxPosLevel+1)*GRID;
        bool cn=bid<=s.b.zero+(s.b.minNegLevel-1)*GRID;
        if(cp){
            while(s.alive&&s.b.active&&bid>=s.b.zero+(s.b.maxPosLevel+1)*GRID){
                q=liq(s.b,bid,ask);if(q>0){closeBasket(s,bid,ask,true,false);break;}
                s.b.maxPosLevel++;addOrder(s,1,bid,ask);if(!s.alive)break;
                q=liq(s.b,bid,ask);if(s.ds.realized+q>=DAILY_TARGET-1e-12){closeBasket(s,bid,ask,false,false);break;}
            }
        }else if(cn){
            while(s.alive&&s.b.active&&bid<=s.b.zero+(s.b.minNegLevel-1)*GRID){
                q=liq(s.b,bid,ask);if(q>0){closeBasket(s,bid,ask,true,false);break;}
                s.b.minNegLevel--;addOrder(s,-1,bid,ask);if(!s.alive)break;
                q=liq(s.b,bid,ask);if(s.ds.realized+q>=DAILY_TARGET-1e-12){closeBasket(s,bid,ask,false,false);break;}
            }
        }
        if(!s.alive){printDay(s);return 0;}
    }
    if(haveDay){if(s.alive&&wd(s.ds.date)==5&&s.b.active)closeBasket(s,s.lastBid,s.lastAsk,false,true);printDay(s);}return 0;
}

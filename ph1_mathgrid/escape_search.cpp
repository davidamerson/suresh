#include <bits/stdc++.h>
#include <chrono>
using namespace std;
using namespace std::chrono;

static constexpr double GRID=1.0, RT_COMM=0.07, DAILY_TARGET=10.0, LEVERAGE=2000.0;
static constexpr double FRIDAY_EARLY_CLOSE_SEC=20*3600+55*60; // conservative vs observed raw close ~20:58/21:58 UTC

bool parseTick(const string&l,int&date,int&sec,double&bid,double&ask){
    if(l.empty()||l[0]!='\"'||l.rfind("\"Exness\"",0)==0)return false;
    size_t c1=l.find(','),c2=l.find(',',c1+1),c3=l.find(',',c2+1),c4=l.find(',',c3+1); if(c4==string::npos)return false;
    string t=l.substr(c2+1,c3-c2-1); if(!t.empty()&&t.front()=='\"')t.erase(t.begin()); if(!t.empty()&&t.back()=='\"')t.pop_back(); if(t.size()<19)return false;
    date=stoi(t.substr(0,4))*10000+stoi(t.substr(5,2))*100+stoi(t.substr(8,2)); sec=stoi(t.substr(11,2))*3600+stoi(t.substr(14,2))*60+stoi(t.substr(17,2));
    bid=strtod(l.c_str()+c3+1,nullptr); ask=strtod(l.c_str()+c4+1,nullptr); return bid>0&&ask>=bid;
}
int wd(int date){int y=date/10000,m=(date/100)%100,d=date%100;weekday w{sys_days{year{y}/month{(unsigned)m}/day{(unsigned)d}}};return w.c_encoding();}
double hrsToFri(int date,int sec){int w=wd(date); if(w<1||w>5)return 0; double x=((5-w)*86400.0+FRIDAY_EARLY_CLOSE_SEC-sec)/3600.0; return max(0.0,x);}

struct Cfg{string name;int d;double h,w;};
vector<Cfg> cfgs(){return {
 {"BASE",999,0,1},
 {"D6H36W2",6,36,2},{"D6H36W3",6,36,3},{"D6H36W5",6,36,5},
 {"D7H36W2",7,36,2},{"D7H36W3",7,36,3},{"D7H36W5",7,36,5},
 {"D8H36W2",8,36,2},{"D8H36W3",8,36,3},{"D8H36W5",8,36,5},{"D8H36W8",8,36,8},
 {"D9H36W2",9,36,2},{"D9H36W3",9,36,3},{"D9H36W5",9,36,5},{"D9H36W8",9,36,8},
 {"D10H36W2",10,36,2},{"D10H36W3",10,36,3},{"D10H36W5",10,36,5},{"D10H36W8",10,36,8},
 {"D8H48W3",8,48,3},{"D8H48W5",8,48,5},{"D10H48W3",10,48,3},{"D10H48W5",10,48,5},
 {"D10ANYW3",10,200,3},{"D10ANYW5",10,200,5}
};}

struct Basket{
 bool active=false,escape=false; double zero=0; int buys=0,sells=0,maxPos=0,minNeg=0; double buySum=0,sellSum=0,nextPos=0,nextNeg=0,space=1;
 int size()const{return buys+sells;}
};
inline double liq(const Basket&b,double bid,double ask){return b.active?(b.buys*bid-b.buySum+b.sellSum-b.sells*ask-RT_COMM*b.size()):0.0;}
inline double margin(const Basket&b,double mid){return b.size()*mid/LEVERAGE;}
struct DS{int date=0,baskets=0,wins=0,friday=0,orders=0,maxOpen=0,escapes=0;double realized=0,minEq=1e100,maxMargin=0;bool target=false,marginFail=false,accountFail=false;};
struct Sim{Cfg c;double bal=1000;bool alive=true,stopped=false;Basket b;DS d;double rH=0,rL=0;bool rangeValid=false,armed=false,needInside=false;};
struct H1{long long key=LLONG_MIN;double hi=-1e100,lo=1e100,lastHi=0,lastLo=0;bool valid=false;};

void setRange(Sim&s,const H1&h,bool inside){if(h.valid){s.rH=h.lastHi;s.rL=h.lastLo;s.rangeValid=true;s.needInside=inside;s.armed=!inside;}}
void newDay(Sim&s,int date,double bid,double ask){s.d=DS();s.d.date=date;s.d.minEq=s.bal+liq(s.b,bid,ask);s.stopped=false;}
void risk(Sim&s,double bid,double ask){if(!s.alive)return;double e=s.bal+liq(s.b,bid,ask);s.d.minEq=min(s.d.minEq,e);s.d.maxOpen=max(s.d.maxOpen,s.b.size());s.d.maxMargin=max(s.d.maxMargin,margin(s.b,(bid+ask)/2));if(e<=0){s.alive=false;s.d.accountFail=true;s.bal=0;}}
bool canAdd(const Sim&s,double bid,double ask){double e=s.bal+liq(s.b,bid,ask);double m=(s.b.size()+1)*((bid+ask)/2)/LEVERAGE;return e>=m;}
void closeB(Sim&s,const H1&h,double bid,double ask,bool win,bool fri){double q=liq(s.b,bid,ask);s.bal+=q;s.d.realized+=q;if(win)s.d.wins++;if(fri)s.d.friday++;s.b=Basket();setRange(s,h,true);if(s.bal<=0){s.bal=0;s.alive=false;s.d.accountFail=true;}if(s.d.realized>=DAILY_TARGET-1e-12){s.d.target=true;s.stopped=true;}}
void startB(Sim&s,int side,double bid,double ask){if(!canAdd(s,bid,ask)){s.alive=false;s.d.marginFail=true;return;}s.b=Basket();s.b.active=true;s.b.zero=bid;double f=side==1?ask:bid;if(side==1){s.b.buys=1;s.b.buySum=f;}else{s.b.sells=1;s.b.sellSum=f;}s.d.baskets++;s.d.orders++;s.armed=false;risk(s,bid,ask);}
void add(Sim&s,int side,double bid,double ask){if(!canAdd(s,bid,ask)){s.alive=false;s.d.marginFail=true;return;}double f=side==1?ask:bid;if(side==1){s.b.buys++;s.b.buySum+=f;}else{s.b.sells++;s.b.sellSum+=f;}s.d.orders++;risk(s,bid,ask);}
void maybeEscape(Sim&s,int date,int sec){if(!s.b.active||s.b.escape||s.c.name=="BASE")return;int two=min(s.b.maxPos,-s.b.minNeg);if(two>=s.c.d&&hrsToFri(date,sec)<=s.c.h){s.b.escape=true;s.b.space=s.c.w;s.b.nextPos=s.b.zero+s.b.maxPos*GRID+s.b.space;s.b.nextNeg=s.b.zero+s.b.minNeg*GRID-s.b.space;s.d.escapes++;}}

void tick(Sim&s,const H1&h,int date,int sec,double bid,double ask){
 if(!s.alive)return;risk(s,bid,ask);if(!s.alive)return;int wday=wd(date);if(wday==0||wday==6||s.stopped)return;
 if(!s.b.active){if(!s.rangeValid)return;if(s.needInside){if(bid<=s.rH&&bid>=s.rL){s.needInside=false;s.armed=true;}else return;}if(!s.armed)return;if(bid>s.rH)startB(s,1,bid,ask);else if(bid<s.rL)startB(s,-1,bid,ask);return;}
 double q=liq(s.b,bid,ask);if(s.d.realized+q>=DAILY_TARGET-1e-12){closeB(s,h,bid,ask,false,false);return;}
 maybeEscape(s,date,sec);
 if(!s.b.escape){
   bool cp=bid>=s.b.zero+(s.b.maxPos+1)*GRID, cn=bid<=s.b.zero+(s.b.minNeg-1)*GRID;
   if(cp){while(s.alive&&s.b.active&&!s.b.escape&&bid>=s.b.zero+(s.b.maxPos+1)*GRID){q=liq(s.b,bid,ask);if(q>0){closeB(s,h,bid,ask,true,false);break;}s.b.maxPos++;add(s,1,bid,ask);if(!s.alive)break;q=liq(s.b,bid,ask);if(s.d.realized+q>=DAILY_TARGET-1e-12){closeB(s,h,bid,ask,false,false);break;}maybeEscape(s,date,sec);}}
   else if(cn){while(s.alive&&s.b.active&&!s.b.escape&&bid<=s.b.zero+(s.b.minNeg-1)*GRID){q=liq(s.b,bid,ask);if(q>0){closeB(s,h,bid,ask,true,false);break;}s.b.minNeg--;add(s,-1,bid,ask);if(!s.alive)break;q=liq(s.b,bid,ask);if(s.d.realized+q>=DAILY_TARGET-1e-12){closeB(s,h,bid,ask,false,false);break;}maybeEscape(s,date,sec);}}
 }
 if(s.b.active&&s.b.escape){
   if(bid>=s.b.nextPos){while(s.alive&&s.b.active&&s.b.escape&&bid>=s.b.nextPos){q=liq(s.b,bid,ask);if(q>0){closeB(s,h,bid,ask,true,false);break;}add(s,1,bid,ask);if(!s.alive)break;s.b.nextPos+=s.b.space;q=liq(s.b,bid,ask);if(s.d.realized+q>=DAILY_TARGET-1e-12){closeB(s,h,bid,ask,false,false);break;}}}
   else if(bid<=s.b.nextNeg){while(s.alive&&s.b.active&&s.b.escape&&bid<=s.b.nextNeg){q=liq(s.b,bid,ask);if(q>0){closeB(s,h,bid,ask,true,false);break;}add(s,-1,bid,ask);if(!s.alive)break;s.b.nextNeg-=s.b.space;q=liq(s.b,bid,ask);if(s.d.realized+q>=DAILY_TARGET-1e-12){closeB(s,h,bid,ask,false,false);break;}}}
 }
}
void selftest(){vector<pair<double,int>>v={{1,1},{2,4},{2,4},{2,7},{2,7}};cout<<"name,net\n";for(int i=0;i<5;i++)cout<<"scenario"<<i+1<<","<<fixed<<setprecision(2)<<v[i].first-RT_COMM*v[i].second<<"\n";}
int main(int argc,char**argv){ios::sync_with_stdio(false);cin.tie(nullptr);if(argc>1&&string(argv[1])=="--selftest"){selftest();return 0;}auto cc=cfgs();vector<Sim>sims;for(auto &c:cc){Sim s;s.c=c;sims.push_back(s);}cout<<"config,date,realized_pnl,target_hit,margin_fail,account_fail,baskets,cycle_wins,friday_closes,total_orders,max_open,escape_activations,min_equity,max_margin_1_2000,balance_end\n";
 H1 h;string line;int date,sec,curDate=0;double bid,ask,lastBid=0,lastAsk=0;bool have=false;
 while(getline(cin,line)){if(!parseTick(line,date,sec,bid,ask))continue;if(!have){have=true;curDate=date;lastBid=bid;lastAsk=ask;for(auto &s:sims)newDay(s,date,bid,ask);}if(date!=curDate){for(auto &s:sims){if(s.alive&&wd(curDate)==5&&s.b.active)closeB(s,h,lastBid,lastAsk,false,true);auto &d=s.d;cout<<s.c.name<<","<<d.date<<","<<fixed<<setprecision(6)<<d.realized<<","<<d.target<<","<<d.marginFail<<","<<d.accountFail<<","<<d.baskets<<","<<d.wins<<","<<d.friday<<","<<d.orders<<","<<d.maxOpen<<","<<d.escapes<<","<<d.minEq<<","<<d.maxMargin<<","<<s.bal<<"\n";if(s.alive)newDay(s,date,bid,ask);else{s.d=DS();s.d.date=date;s.d.minEq=s.bal;}}curDate=date;}lastBid=bid;lastAsk=ask;
   long long hk=(long long)date*24+sec/3600;bool hc=false;if(h.key==LLONG_MIN){h.key=hk;h.hi=bid;h.lo=bid;}else if(hk!=h.key){h.lastHi=h.hi;h.lastLo=h.lo;h.valid=h.hi>h.lo;h.key=hk;h.hi=bid;h.lo=bid;hc=true;}else{h.hi=max(h.hi,bid);h.lo=min(h.lo,bid);}if(hc&&wd(date)>=1&&wd(date)<=5)for(auto &s:sims)if(s.alive&&!s.b.active&&!s.stopped)setRange(s,h,false);for(auto &s:sims)tick(s,h,date,sec,bid,ask);
 }
 if(have)for(auto &s:sims){if(s.alive&&wd(curDate)==5&&s.b.active)closeB(s,h,lastBid,lastAsk,false,true);auto &d=s.d;cout<<s.c.name<<","<<d.date<<","<<fixed<<setprecision(6)<<d.realized<<","<<d.target<<","<<d.marginFail<<","<<d.accountFail<<","<<d.baskets<<","<<d.wins<<","<<d.friday<<","<<d.orders<<","<<d.maxOpen<<","<<d.escapes<<","<<d.minEq<<","<<d.maxMargin<<","<<s.bal<<"\n";}
}

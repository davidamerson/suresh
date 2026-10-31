#include <bits/stdc++.h>
using namespace std;
static constexpr double D1=2.0, D2=6.0, TARGET=0.70, C=0.035;
static constexpr int WIDEN_AFTER=5;
static constexpr int GAP_SEC=900; // detect daily market break after 20:00

enum Mode { BASE, EXTREV, EXTHOLD, EXTWIDE };
struct S{int y=0,m=0,d=0; bool active=false,em=false,ref=false; double rmid=0; int pos=0; double ep=0,emid=0,real=0,minliq=0; int rev=0; double lb=0,la=0; int lsec=-1; string side="";};
int wd(int y,int m,int d){static int t[]={0,3,2,5,0,3,5,1,4,6,2,4}; if(m<3)y--; int w=(y+y/4-y/100+y/400+t[m-1]+d)%7; return w==0?6:w-1;}
string ds(int y,int m,int d){char b[16];snprintf(b,sizeof(b),"%04d-%02d-%02d",y,m,d);return b;}
string ts(int s){if(s<0)return"";char b[16];snprintf(b,sizeof(b),"%02d:%02d:%02d",s/3600,(s%3600)/60,s%60);return b;}
inline double op(const S&s,double b,double a){return s.pos==1?b-s.ep:s.pos==-1?s.ep-a:0;}
inline double liq(const S&s,double b,double a){return s.pos?s.real+op(s,b,a)-C:s.real;}
void emit(S&s,double pnl,string reason,int sec,bool hit){if(s.em||!s.active)return;s.em=true;cout<<fixed<<setprecision(6)<<ds(s.y,s.m,s.d)<<","<<(hit?1:0)<<","<<pnl<<","<<s.rev<<","<<s.minliq<<","<<s.side<<","<<reason<<","<<ts(sec)<<"\n";}
void closeat(S&s,double b,double a,int sec,string why,bool hit){if(s.pos){s.real+=op(s,b,a)-C;s.pos=0;}s.minliq=min(s.minliq,s.real);emit(s,s.real,why,sec,hit);}
void fin(S&s){if(!s.active||s.em)return;if(s.pos)closeat(s,s.lb,s.la,s.lsec,"DAY_LAST",false);else emit(s,s.real,"DAY_LAST_FLAT",s.lsec,false);}
bool parse(const string&l,int&y,int&m,int&d,int&sec,double&b,double&a){if(l.empty()||l[0]!='\"'||l.rfind("\"Exness\"",0)==0)return false;size_t c1=l.find(','),c2=l.find(',',c1+1),c3=l.find(',',c2+1),c4=l.find(',',c3+1);if(c4==string::npos)return false;string t=l.substr(c2+1,c3-c2-1);if(t.front()=='\"')t.erase(t.begin());if(!t.empty()&&t.back()=='\"')t.pop_back();if(t.size()<19)return false;y=stoi(t.substr(0,4));m=stoi(t.substr(5,2));d=stoi(t.substr(8,2));sec=stoi(t.substr(11,2))*3600+stoi(t.substr(14,2))*60+stoi(t.substr(17,2));b=strtod(l.c_str()+c3+1,nullptr);a=strtod(l.c_str()+c4+1,nullptr);return b>0&&a>0;}
int main(int argc,char**argv){Mode mode=BASE;if(argc>1){string q=argv[1];if(q=="EXTREV")mode=EXTREV;else if(q=="EXTHOLD")mode=EXTHOLD;else if(q=="EXTWIDE")mode=EXTWIDE;}
ios::sync_with_stdio(false);cin.tie(nullptr);cout<<"date,target_hit,final_pnl,reversals,min_liq,entry_side,exit_reason,exit_time\n";S s;string l;while(getline(cin,l)){int y,m,d,sec;double b,a;if(!parse(l,y,m,d,sec,b,a))continue;int nk=y*10000+m*100+d,ok=s.y*10000+s.m*100+s.d;
 if(!s.active||nk!=ok){fin(s);s=S{};s.y=y;s.m=m;s.d=d;s.active=wd(y,m,d)<=4;s.minliq=0;}
 if(!s.active||s.em)continue;
 // If extended mode and we encounter the first post-20 daily market break, liquidate on previous quote.
 if(mode!=BASE && s.lsec>=20*3600 && sec>s.lsec && sec-s.lsec>GAP_SEC){if(s.pos)closeat(s,s.lb,s.la,s.lsec,"MARKET_BREAK",false);else emit(s,s.real,"MARKET_BREAK_FLAT",s.lsec,false);continue;}
 double mid=(b+a)/2;s.lb=b;s.la=a;s.lsec=sec;
 if(sec<6*3600)continue;
 if(mode==BASE && sec>=20*3600){if(s.pos)closeat(s,b,a,sec,"20UTC_FLAT",false);else emit(s,s.real,"20UTC_FLAT",sec,false);continue;}
 // After 20 in extension modes: do not start a new position, only manage an already-open recovery.
 if(!s.ref){if(sec>=20*3600){emit(s,0,"NO_CYCLE",sec,false);continue;}s.ref=true;s.rmid=mid;continue;}
 if(!s.pos){if(sec>=20*3600){emit(s,s.real,"20UTC_FLAT",sec,false);continue;}if(mid>=s.rmid+D1){s.pos=1;s.ep=a;s.emid=mid;s.real-=C;s.side="BUY";s.minliq=min(s.minliq,liq(s,b,a));}else if(mid<=s.rmid-D1){s.pos=-1;s.ep=b;s.emid=mid;s.real-=C;s.side="SELL";s.minliq=min(s.minliq,liq(s,b,a));}continue;}
 double q=liq(s,b,a);s.minliq=min(s.minliq,q);if(q>=TARGET){closeat(s,b,a,sec,"TARGET",true);continue;}
 bool late=sec>=20*3600; if(late && mode==EXTHOLD) continue;
 double rd=(s.rev<WIDEN_AFTER)?D1:D2; if(late&&mode==EXTWIDE)rd=max(rd,12.0);
 bool rv=(s.pos==1&&mid<=s.emid-rd)||(s.pos==-1&&mid>=s.emid+rd);if(rv){s.real+=op(s,b,a)-C;int old=s.pos;s.pos=-old;s.real-=C;s.ep=s.pos==1?a:b;s.emid=mid;s.rev++;s.minliq=min(s.minliq,liq(s,b,a));}
 }fin(s);}

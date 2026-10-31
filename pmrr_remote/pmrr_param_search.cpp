#include <bits/stdc++.h>
using namespace std;
static constexpr double ENTRY=2.0,TARGET=0.70,C=0.035;
struct Param{int n1;double d1;int n2;double d2;};
struct St{bool ref=false,done=false,opened=false;double rmid=0;int pos=0;double ep=0,emid=0,real=0,minliq=0;int rev=0;};
struct Agg{int pass=0,days=0,maxrev=0;double total=0,worst=1e100,worstdd=1e100;vector<pair<int,double>> daily;};
inline double op(const St&s,double b,double a){return s.pos==1?b-s.ep:s.pos==-1?s.ep-a:0;}
inline double liq(const St&s,double b,double a){return s.pos?s.real+op(s,b,a)-C:s.real;}
bool parse(const string&l,int&date,int&sec,double&b,double&a){if(l.empty()||l[0]!='\"'||l.rfind("\"Exness\"",0)==0)return false;size_t c1=l.find(','),c2=l.find(',',c1+1),c3=l.find(',',c2+1),c4=l.find(',',c3+1);if(c4==string::npos)return false;string t=l.substr(c2+1,c3-c2-1);if(t.front()=='\"')t.erase(t.begin());if(!t.empty()&&t.back()=='\"')t.pop_back();if(t.size()<19)return false;date=stoi(t.substr(0,4))*10000+stoi(t.substr(5,2))*100+stoi(t.substr(8,2));sec=stoi(t.substr(11,2))*3600+stoi(t.substr(14,2))*60+stoi(t.substr(17,2));b=strtod(l.c_str()+c3+1,nullptr);a=strtod(l.c_str()+c4+1,nullptr);return b>0&&a>0;}
int main(){ios::sync_with_stdio(false);cin.tie(nullptr);
 vector<int> wanted={20250114,20250509,20250625,20250815,20250929,20251008,20251215,20251218};unordered_set<int> W(wanted.begin(),wanted.end());
 vector<Param>P;for(int n1:{3,4,5,6})for(double d1:{4.0,6.0,8.0,10.0})for(int n2:{7,9,11,13})if(n2>n1)for(double d2:{6.0,8.0,12.0,16.0,24.0,40.0,9999.0})P.push_back({n1,d1,n2,d2});
 vector<St>S(P.size());vector<Agg>A(P.size());int cur=0;double lb=0,la=0;int lsec=-1;bool have=false;
 auto finish=[&](int date,double b,double a){if(!have||!W.count(date))return;for(size_t i=0;i<P.size();++i){auto&s=S[i];if(s.done)continue;if(s.pos){s.real+=op(s,b,a)-C;s.pos=0;}s.minliq=min(s.minliq,s.real);s.done=true;auto&g=A[i];g.days++;g.total+=s.real;g.worst=min(g.worst,s.real);g.worstdd=min(g.worstdd,s.minliq);g.maxrev=max(g.maxrev,s.rev);if(s.real>0)g.pass++;g.daily.push_back({date,s.real});}};
 string l;while(getline(cin,l)){int date,sec;double b,a;if(!parse(l,date,sec,b,a))continue;if(cur && date!=cur){finish(cur,lb,la);for(auto&s:S)s=St{};have=false;}cur=date;lb=b;la=a;lsec=sec;if(!W.count(date))continue;have=true;double mid=(b+a)/2;
 for(size_t i=0;i<P.size();++i){auto&s=S[i];if(s.done)continue;if(sec<21600)continue;if(sec>=72000){if(s.pos){s.real+=op(s,b,a)-C;s.pos=0;}s.minliq=min(s.minliq,s.real);s.done=true;auto&g=A[i];g.days++;g.total+=s.real;g.worst=min(g.worst,s.real);g.worstdd=min(g.worstdd,s.minliq);g.maxrev=max(g.maxrev,s.rev);if(s.real>0)g.pass++;g.daily.push_back({date,s.real});continue;}
   if(!s.ref){s.ref=true;s.rmid=mid;continue;}
   if(!s.pos){if(mid>=s.rmid+ENTRY){s.pos=1;s.ep=a;s.emid=mid;s.real-=C;s.opened=true;s.minliq=min(s.minliq,liq(s,b,a));}else if(mid<=s.rmid-ENTRY){s.pos=-1;s.ep=b;s.emid=mid;s.real-=C;s.opened=true;s.minliq=min(s.minliq,liq(s,b,a));}continue;}
   double q=liq(s,b,a);s.minliq=min(s.minliq,q);if(q>=TARGET){s.real+=op(s,b,a)-C;s.pos=0;s.done=true;auto&g=A[i];g.days++;g.total+=s.real;g.worst=min(g.worst,s.real);g.worstdd=min(g.worstdd,s.minliq);g.maxrev=max(g.maxrev,s.rev);if(s.real>0)g.pass++;g.daily.push_back({date,s.real});continue;}
   double rd=s.rev<P[i].n1?ENTRY:(s.rev<P[i].n2?P[i].d1:P[i].d2);bool rv=(s.pos==1&&mid<=s.emid-rd)||(s.pos==-1&&mid>=s.emid+rd);if(rv){s.real+=op(s,b,a)-C;int old=s.pos;s.pos=-old;s.real-=C;s.ep=s.pos==1?a:b;s.emid=mid;s.rev++;s.minliq=min(s.minliq,liq(s,b,a));}
 }}
 if(cur)finish(cur,lb,la);
 vector<int>idx(P.size());iota(idx.begin(),idx.end(),0);sort(idx.begin(),idx.end(),[&](int i,int j){if(A[i].pass!=A[j].pass)return A[i].pass>A[j].pass;if(A[i].worst!=A[j].worst)return A[i].worst>A[j].worst;if(A[i].total!=A[j].total)return A[i].total>A[j].total;return A[i].worstdd>A[j].worstdd;});
 cout<<"rank,n1,d1,n2,d2,pass,days,total,worst,worstdd,maxrev,daily\n";int rank=0;for(int i:idx){if(rank>=80)break;auto&p=P[i];auto&g=A[i];cout<<++rank<<","<<p.n1<<","<<p.d1<<","<<p.n2<<","<<(p.d2>1000?9999:p.d2)<<","<<g.pass<<","<<g.days<<","<<fixed<<setprecision(6)<<g.total<<","<<g.worst<<","<<g.worstdd<<","<<g.maxrev<<",\"";for(auto &x:g.daily)cout<<x.first<<":"<<x.second<<";";cout<<"\"\n";}
}

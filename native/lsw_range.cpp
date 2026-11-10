// Native unit-count operator by Zijia Wang.
// Core adapted from the authors' C++ research implementation of LocalWindows
// and its exact baselines; the native solver functions are retained verbatim.
// See ../docs/provenance.md for the source SHA-256. Only the benchmark/timing
// driver has been replaced with a single-solve CLI.
#include <algorithm>
#include <chrono>
#include <iomanip>
#include <iostream>
#include <map>
#include <numeric>
#include <stdexcept>
#include <string>
#include <vector>
using namespace std;using Clock=chrono::steady_clock;constexpr int INF=1000000000;
struct Row{int lo,hi,w=1;};
bool hit(const Row&r,int x){return r.lo<=x&&x<=r.hi;}
bool same(const Row&a,const Row&b){return a.lo==b.lo&&a.hi==b.hi;}
struct Diagnostics{
 long long windows=0,incidences=0,dp_cells=0,transition_updates=0,prefix_steps=0,workspace_bytes=0,bookkeeping_bytes=0;
 int max_local_states=0,global_states=0;bool common_fast=false;
};
struct Prepared{int n=0,dlo=0,dhi=0,k=0,offset=0,static_lo=0,static_hi=0;vector<Row>runs;vector<pair<int,int>>events;vector<int>static_counts;};
struct Result{vector<pair<int,int>>answers;Diagnostics d;int active_rows=0,runs=0,static_lo=0,static_hi=0;double prepare_seconds=0,solve_seconds=0;};
long long common_bytes(const Prepared&p){return p.runs.size()*sizeof(Row)+p.events.size()*sizeof(pair<int,int>)+p.static_counts.size()*sizeof(int);}
Prepared prepare(const vector<Row>&input,int dlo,int dhi){
 if(dlo>dhi)throw runtime_error("empty state domain");
 Prepared p;p.n=input.size();p.dlo=dlo;p.dhi=dhi;
 for(auto z:input){if(z.w!=1)throw runtime_error("external weights must be unit");z.lo=max(z.lo,dlo);z.hi=min(z.hi,dhi);if(z.lo>z.hi)continue;if(z.lo==dlo&&z.hi==dhi){++p.offset;continue;}++p.k;if(!p.runs.empty()&&same(p.runs.back(),z))++p.runs.back().w;else p.runs.push_back(z);}
 map<int,int>events;events[dlo]=0;for(auto z:p.runs){events[z.lo]+=z.w;if(z.hi<dhi)events[z.hi+1]-=z.w;}
 int count=p.offset;p.static_lo=INF;p.static_hi=-1;
 for(auto [x,delta]:events){count+=delta;p.events.push_back({x,delta});p.static_counts.push_back(count);p.static_lo=min(p.static_lo,count);p.static_hi=max(p.static_hi,count);}return p;
}
vector<int>static_at(const Prepared&p,const vector<int>&starts){vector<int>out;size_t j=0;int c=p.offset;for(int x:starts){while(j<p.events.size()&&p.events[j].first<=x)c+=p.events[j++].second;out.push_back(c);}return out;}
vector<int>support(const Prepared&p){vector<int>x{p.dlo,p.dhi};for(auto z:p.runs)for(int t:{z.lo-1,z.lo,z.hi,z.hi+1})if(t>=p.dlo&&t<=p.dhi)x.push_back(t);sort(x.begin(),x.end());x.erase(unique(x.begin(),x.end()),x.end());return x;}
// Shared exact at-most-budget metric closure on weighted runs. Each direction
// charges actual integer state gaps. Cheap resource cap is a constructive upper
// bound (r-1)*span; no O(rm) exact-saturation oracle is supplied to any plan.
vector<pair<int,int>>budget_kernel(const vector<Row>&rows,const vector<int>&x,int offset,const vector<int>&queries,Diagnostics&d){
 long long cap=1LL*max(0,int(rows.size())-1)*(x.back()-x.front());
 int V=min<long long>(*max_element(queries.begin(),queries.end()),cap),B=V+1,m=x.size();vector<int>lo(size_t(m)*B,0),hi(lo.size(),0);
 d.workspace_bytes=max<long long>(d.workspace_bytes,2LL*m*B*sizeof(int));d.max_local_states=max(d.max_local_states,m);
 for(auto z:rows){
  for(int j=1;j<m;++j){int gap=x[j]-x[j-1];for(int v=gap;v<B;++v){lo[j*B+v]=min(lo[j*B+v],lo[(j-1)*B+v-gap]);hi[j*B+v]=max(hi[j*B+v],hi[(j-1)*B+v-gap]);++d.transition_updates;}}
  for(int j=m-2;j>=0;--j){int gap=x[j+1]-x[j];for(int v=gap;v<B;++v){lo[j*B+v]=min(lo[j*B+v],lo[(j+1)*B+v-gap]);hi[j*B+v]=max(hi[j*B+v],hi[(j+1)*B+v-gap]);++d.transition_updates;}}
  for(int j=0;j<m;++j){int add=z.w*hit(z,x[j]);for(int v=0;v<B;++v){lo[j*B+v]+=add;hi[j*B+v]+=add;}}d.dp_cells+=1LL*m*B;
 }
 vector<pair<int,int>>out;for(int requested:queries){int v=min(requested,V),a=INF,b=-1;for(int j=0;j<m;++j){a=min(a,lo[j*B+v]);b=max(b,hi[j*B+v]);}out.push_back({a+offset,b+offset});}return out;
}
vector<pair<int,int>>global_bank(const Prepared&p,const vector<int>&q,Diagnostics&d){auto x=support(p);d.global_states=x.size();d.windows=1;d.incidences=p.runs.size();d.bookkeeping_bytes+=x.size()*sizeof(int);return budget_kernel(p.runs,x,p.offset,q,d);}
struct Local{int start=0,end=0;vector<Row>rows;vector<int>states;};
// Build once at max requested V. Every smaller-budget feasible path is covered.
// Event incidences preserve time order, and omitted constant windows are covered
// by exact static global extrema. LocalWindows V=1 uses weighted prefix extrema.
vector<pair<int,int>>local_bank(const Prepared&p,const vector<int>&q,bool gaps,Diagnostics&d,bool generic=false){
 int V=*max_element(q.begin(),q.end());vector<pair<int,int>>result(q.size(),{p.static_lo,p.static_hi});if(V==0)return result;
 map<int,Local>locals;vector<int>x,component,start_index,end_index;int M=p.dhi-p.dlo+1,blocks=(M+V-1)/V;
 if(gaps){x=support(p);d.global_states=max(d.global_states,int(x.size()));component.resize(x.size());int c=0;start_index.push_back(0);for(int j=0;j<int(x.size());++j){if(j&&x[j]-x[j-1]>V){end_index.push_back(j-1);start_index.push_back(j);++c;}component[j]=c;}end_index.push_back(int(x.size())-1);}
 for(auto z:p.runs){vector<int>ids;
  if(!gaps&&blocks==1)ids.push_back(0);
  else for(int edge:{z.lo,z.hi+1}){if(edge<=p.dlo||edge>p.dhi)continue;
   if(gaps){auto it=lower_bound(x.begin(),x.end(),edge);if(it==x.end()||*it!=edge)throw runtime_error("missing critical edge");int j=it-x.begin();if(!j||x[j-1]!=edge-1||component[j-1]!=component[j])throw runtime_error("split unit edge");ids.push_back(component[j]);}
   else{int b=(edge-p.dlo)/V;for(int id:{b-1,b})if(id>=0&&id<blocks-1){int a=p.dlo+id*V,t=min(p.dhi,p.dlo+(id+2)*V-1);if(a<=edge-1&&edge<=t)ids.push_back(id);}}
  }
  sort(ids.begin(),ids.end());ids.erase(unique(ids.begin(),ids.end()),ids.end());if(ids.size()>size_t(gaps?2:4))throw runtime_error("incidence bound exceeded");
  for(int id:ids){auto&l=locals[id];if(l.rows.empty()){if(gaps){l.start=x[start_index[id]];l.end=x[end_index[id]];l.states.assign(x.begin()+start_index[id],x.begin()+end_index[id]+1);}else{l.start=blocks==1?p.dlo:p.dlo+id*V;l.end=blocks==1?p.dhi:min(p.dhi,p.dlo+(id+2)*V-1);}}
   if((z.hi<l.start||z.lo>l.end)||(z.lo<=l.start&&z.hi>=l.end))throw runtime_error("constant local incidence");
   l.rows.push_back(z);++d.incidences;
  }
 }
 vector<int>starts;for(auto&[id,l]:locals)starts.push_back(l.start);auto base=static_at(p,starts);int index=0;long long incidence_bytes=0;
 for(auto&[id,l]:locals){int offset=base[index++];for(auto z:l.rows)offset-=z.w*hit(z,l.start);if(!gaps){l.states.resize(l.end-l.start+1);iota(l.states.begin(),l.states.end(),l.start);}vector<pair<int,int>>answers;
  if(!gaps&&!generic&&V==1&&l.end==l.start+1){int at_start=offset,total=0,lo_prefix=0,hi_prefix=0;for(auto z:l.rows){at_start+=z.w*hit(z,l.start);total+=z.w*(int(hit(z,l.end))-int(hit(z,l.start)));lo_prefix=min(lo_prefix,total);hi_prefix=max(hi_prefix,total);++d.prefix_steps;}
   for(int v:q){int a=v==0?min(0,total):min({0,total,lo_prefix,total-hi_prefix});int b=v==0?max(0,total):max({0,total,hi_prefix,total-lo_prefix});answers.push_back({at_start+a,at_start+b});}d.max_local_states=max(d.max_local_states,2);
  }else answers=budget_kernel(l.rows,l.states,offset,q,d);
  for(size_t j=0;j<q.size();++j){result[j].first=min(result[j].first,answers[j].first);result[j].second=max(result[j].second,answers[j].second);}++d.windows;
  incidence_bytes+=l.rows.size()*sizeof(Row)+sizeof(Local)+sizeof(int);
  if(!gaps){
   long long cap=1LL*max(0,int(l.rows.size())-1)*(l.end-l.start);
   long long dp_bytes=!generic&&V==1&&l.end==l.start+1?0:2LL*l.states.size()*(min<long long>(V,cap)+1)*sizeof(int);
   d.workspace_bytes=max<long long>(d.workspace_bytes,dp_bytes+l.states.size()*sizeof(int));vector<int>().swap(l.states);
  }else incidence_bytes+=l.states.size()*sizeof(int);
 }
 d.bookkeeping_bytes=max<long long>(d.bookkeeping_bytes,common_bytes(p)+incidence_bytes+(starts.size()+base.size()+x.size()+component.size()+start_index.size()+end_index.size())*sizeof(int));return result;
}
void transform(int*a,const vector<int>&x){for(int j=1;j<int(x.size());++j)a[j]=min(a[j],a[j-1]+x[j]-x[j-1]);for(int j=int(x.size())-2;j>=0;--j)a[j]=min(a[j],a[j+1]+x[j+1]-x[j]);}
vector<int>capped_count(const vector<Row>&rows,const vector<int>&x,int cap,bool misses,Diagnostics&d){
 int m=x.size();vector<int>a(size_t(cap+1)*m,INF),b(a.size(),INF);fill(a.begin(),a.begin()+m,0);int used=0;d.workspace_bytes=max<long long>(d.workspace_bytes,(2LL*(cap+1)*m+cap+1)*sizeof(int));d.max_local_states=max(d.max_local_states,m);
 for(auto z:rows){fill(b.begin(),b.end(),INF);for(int c=0;c<=min(cap,used);++c){transform(a.data()+c*m,x);d.transition_updates+=2LL*max(0,m-1);for(int j=0;j<m;++j){int add=z.w*(misses?!hit(z,x[j]):hit(z,x[j]));if(c+add<=cap)b[(c+add)*m+j]=min(b[(c+add)*m+j],a[c*m+j]);}d.dp_cells+=m;}used+=z.w;a.swap(b);}
 vector<int>f(cap+1,INF);for(int c=0;c<=cap;++c)f[c]=*min_element(a.begin()+c*m,a.begin()+(c+1)*m);for(int c=1;c<=cap;++c)f[c]=min(f[c],f[c-1]);return f;
}
vector<pair<int,int>>run_tail(const Prepared&p,const vector<int>&q,Diagnostics&d){
 auto x=support(p);d.global_states=x.size();d.incidences=p.runs.size();d.windows=1;d.bookkeeping_bytes+=x.size()*sizeof(int);vector<int>g(p.n+1,INF);for(int c:p.static_counts)g[c]=0;for(int c=p.static_lo;c<=p.static_hi;++c)if(g[c]!=0)g[c]=1;
 int low=p.static_lo-p.offset,high=p.static_hi-p.offset;if(low>0){auto f=capped_count(p.runs,x,low-1,false,d);for(int c=0;c<low;++c)g[c+p.offset]=f[c];}if(p.k-high>0){auto f=capped_count(p.runs,x,p.k-high-1,true,d);for(int c=0;c<p.k-high;++c)g[p.k-c+p.offset]=f[c];}
 d.workspace_bytes+=g.size()*sizeof(int);vector<pair<int,int>>out;for(int v:q){int a=INF,b=-1;for(int c=0;c<=p.n;++c)if(g[c]<=v){a=min(a,c);b=c;}out.push_back({a,b});}return out;
}
// Independent correctness axis: original unit rows, all original integer
// states, exact count. No fixed-row/run/cover/completion reduction.
vector<pair<int,int>>reference_count(const vector<Row>&input,int dlo,int dhi,const vector<int>&q){
 int n=input.size(),m=dhi-dlo+1;vector<int>x(m);iota(x.begin(),x.end(),dlo);vector<int>a(size_t(n+1)*m,INF),b(a.size(),INF);fill(a.begin(),a.begin()+m,0);int used=0;
 for(auto z:input){fill(b.begin(),b.end(),INF);for(int c=0;c<=used;++c){transform(a.data()+c*m,x);for(int j=0;j<m;++j){int nc=c+hit(z,x[j]);b[nc*m+j]=min(b[nc*m+j],a[c*m+j]);}}++used;a.swap(b);}
 vector<int>g(n+1);for(int c=0;c<=n;++c)g[c]=*min_element(a.begin()+c*m,a.begin()+(c+1)*m);vector<pair<int,int>>out;for(int v:q){int lo=INF,hi=-1;for(int c=0;c<=n;++c)if(g[c]<=v){lo=min(lo,c);hi=c;}out.push_back({lo,hi});}return out;
}
const vector<string>METHODS={"GlobalBudgetBank","GapComponents","LocalWindows","LocalWindowsGeneric","RunTailFullGThenGather"};
Result solve(const string&method,const vector<Row>&input,int dlo,int dhi,const vector<int>&q){
 Result r;auto t0=Clock::now();auto p=prepare(input,dlo,dhi);
 vector<int>unique;vector<int>position(*max_element(q.begin(),q.end())+1,-1);
 for(int v:q)position[v]=0;
 for(int v=0;v<int(position.size());++v)if(position[v]==0){position[v]=unique.size();unique.push_back(v);}
 auto t1=Clock::now();r.active_rows=p.k;r.runs=p.runs.size();r.static_lo=p.static_lo;r.static_hi=p.static_hi;r.d.bookkeeping_bytes=common_bytes(p);
 if(method=="ReferenceFullCount")r.answers=reference_count(input,dlo,dhi,unique);
 else if(unique.back()==0||p.k==0||(p.static_lo==p.offset&&p.static_hi==p.offset+p.k)){r.answers.assign(unique.size(),{p.static_lo,p.static_hi});r.d.common_fast=true;}
 else if(method=="GlobalBudgetBank")r.answers=global_bank(p,unique,r.d);
 else if(method=="RunTailFullGThenGather")r.answers=run_tail(p,unique,r.d);
 else if(method=="LocalWindows"||method=="LocalWindowsGeneric"||method=="GapComponents")r.answers=local_bank(p,unique,method=="GapComponents",r.d,method=="LocalWindowsGeneric");
 else throw runtime_error("unknown method");
 auto unique_answers=move(r.answers);r.answers.reserve(q.size());for(int v:q)r.answers.push_back(unique_answers[position[v]]);
 r.d.bookkeeping_bytes+=(unique.size()+position.size())*sizeof(int);
 auto t2=Clock::now();r.prepare_seconds=chrono::duration<double>(t1-t0).count();r.solve_seconds=chrono::duration<double>(t2-t1).count();return r;
}

// Request protocol: METHOD N DOMAIN_LO DOMAIN_HI Q, Q budgets, then N lo/hi
// pairs. Repeated requests on stdin produce one JSON result each.
int main(int argc, char** argv) {
 ios::sync_with_stdio(false); cin.tie(nullptr);
 if(argc > 1) {
  if(argc == 2 && string(argv[1]) == "--help") {
   cout << "Input: METHOD N DOMAIN_LO DOMAIN_HI Q; Q nonnegative budgets; N inclusive lo/hi pairs.\n"
        << "Methods: LocalWindows, LocalWindowsGeneric, GlobalBudgetBank, GapComponents, RunTailFullGThenGather, ReferenceFullCount.\n"
        << "Unit row weights; free endpoints; one shared at-most total-variation budget.\n";
   return 0;
  }
  cerr << "Use --help or provide requests on standard input.\n"; return 2;
 }
 try {
  string method;
  while(cin >> method) {
   if(method != "ReferenceFullCount" && find(METHODS.begin(), METHODS.end(), method) == METHODS.end())
    throw runtime_error("unknown method");
   int n, a, b, count;
   if(!(cin >> n >> a >> b >> count) || n < 0 || n > 1000000 || a < -1000000 || b > 1000000 || a > b || count < 1 || count > 1000000)
    throw runtime_error("invalid header (N<=1000000, -1000000<=domain<=1000000, 1<=Q<=1000000)");
   vector<int> budgets(count);
   for(auto& v : budgets) if(!(cin >> v) || v < 0 || v > 10000)
    throw runtime_error("budget must be an integer in [0,10000]");
   vector<Row> rows(n);
   for(auto& row : rows) if(!(cin >> row.lo >> row.hi) || row.lo < -1000000000 || row.lo > 1000000000 || row.hi < -1000000000 || row.hi > 1000000000)
    throw runtime_error("interval endpoints must be integers in [-1000000000,1000000000]");
   if(method == "ReferenceFullCount" && 1LL*(n+1)*(b-a+1) > 2000000)
    throw runtime_error("ReferenceFullCount is a small-case oracle (at most 2000000 count/state cells)");
   auto result = solve(method, rows, a, b, budgets);
   cout << "{\"method\":\"" << method << "\",\"budgets\":[";
   for(size_t j=0; j<budgets.size(); ++j) { if(j) cout << ','; cout << budgets[j]; }
   cout << "],\"bounds\":[";
   for(size_t j=0; j<result.answers.size(); ++j) {
    if(j) cout << ',';
    cout << '[' << result.answers[j].first << ',' << result.answers[j].second << ']';
   }
   cout << "]}\n" << flush;
  }
 } catch(const exception& error) {
  cerr << "lsw-native: " << error.what() << '\n'; return 2;
 }
 return 0;
}

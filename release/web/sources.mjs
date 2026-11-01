export function combinedAccounts(snapshot) {
 const mapping=snapshot?.external?.hostkey_identity_map||{}, groups=new Map();
 for(const a of [...(snapshot?.accounts||[]),...(snapshot?.observed_orphans||[])]){
  if(a.disabled===true||a.status==='disabled')continue;
  const id=mapping[a.id]||a.id;
  groups.set(id,{...a,source_titles:['Hostkey'],connections:[],hostkey:true});
 }
 for(const s of snapshot?.external?.sources||[]){
  for(const raw of s.accounts||[]){
   if(raw.disabled===true||raw.status==='disabled')continue;
   const a={...raw,source_status:s.status,source_titles:[s.title],connections:[{title:s.title,status:s.status,problem:raw.data_problem}],hostkey:false};
   const old=groups.get(a.id);
   if(!old){groups.set(a.id,a);continue;}
   const titles=[...new Set([...old.source_titles,s.title])],connections=[...old.connections,...a.connections];
   if(old.hostkey){groups.set(a.id,{...old,source_titles:titles,connections});continue;}
   const score=x=>(x.source_status==='ok'?1e16:0)+(x.quota?.windows?.length?1e15:0)+(Date.parse(x.source_observed_at)||0);
   groups.set(a.id,{...(score(a)>score(old)?a:old),source_titles:titles,connections});
  }
 }
 const logins=snapshot?.external?.account_logins||{};
 return [...groups.entries()].map(([id,a])=>({...a,login:logins[id]||null}));
}

import {freshAt} from './operations-view.mjs';
export function integrationRows(data,now,transportError=false){
 const rows=[];
 for(const i of data?.integrations||[]){
  const good=!transportError&&freshAt(data.collected_at,now,90000)&&freshAt(i.observed_at,now,90000)&&i.status==='ok';
  const records=i.records.length?i.records:[{id:'unavailable',kind:'service',title:i.title,state:i.status==='auth_required'?'auth_required':'unknown',observed_at:i.observed_at}];
  for(const r of records){
   const current=good&&freshAt(r.observed_at,now,90000)&&!['unknown','auth_required'].includes(r.state);
   const quota=k=>current&&(!r[k.replace('remaining','reset_at')]||Date.parse(r[k.replace('remaining','reset_at')])>now)?r[k]??null:null;
   const weekly=quota('weekly_remaining'),five=quota('five_hour_remaining'),low=Math.min(...[weekly,five].filter(x=>x!==null));
   const tone=!current?(r.state==='auth_required'||i.status==='auth_required'?'warning':'unknown'):low<10?'critical':low<25?'warning':r.state;
   rows.push({...r,key:i.id+'-'+r.id,source:i.title,page:r.kind==='account'?'subscriptions':r.kind==='balance'?'balances':'machines',tone,value:current?r.value??null:null,weekly_remaining:weekly,five_hour_remaining:five,problem:!current?(tone==='warning'?'Нужен вход в сервис':'Нет свежих данных'):r.detail||'',current});
  }
 }
 return rows.sort((a,b)=>({critical:0,warning:1,unknown:2,ok:3}[a.tone]-{critical:0,warning:1,unknown:2,ok:3}[b.tone])||(a.weekly_remaining??101)-(b.weekly_remaining??101));
}

const numeric=n=>typeof n==='number'&&Number.isFinite(n);
export const freshAt=(value,now,ttl)=>typeof value==='string'&&Number.isFinite(Date.parse(value))&&now-Date.parse(value)>=-60000&&now-Date.parse(value)<ttl*1000;
const rank={critical:0,warning:1,unknown:2,ok:3};
const errors={auth_error:'Нет доступа к балансу',rate_limited:'Сервис ограничил частоту проверки',not_configured:'Доступ не подключён',invalid_data:'Сервис вернул неполные данные',unavailable:'Не удалось прочитать баланс'};
export function balanceView(b,ops,now=Date.now(),transportError=false){
 const fresh=!transportError&&freshAt(ops?.collected_at,now,90000)&&b.status==='ok'&&freshAt(b.observed_at,now,90000)&&freshAt(b.source_at,now,b.id==='digitalocean'?129600:90000)&&numeric(b.remaining);
 if(!fresh)return {...b,amount:null,tone:'unknown',problem:errors[b.status]||'Нет свежего замера',rank:rank.unknown};
 const billed=b.id==='digitalocean'&&b.accrued_due>0;
 const noPrepayment=b.id==='digitalocean'&&b.remaining===0;
 // Display-only warning thresholds, never provider spending or rate limits.
 const critical=b.unit==='credits'?2000:10,low=b.unit==='credits'?5000:25;
 const tone=noPrepayment?'ok':b.remaining<critical?'critical':b.remaining<low?'warning':'ok';
 return {...b,amount:billed?b.accrued_due:b.remaining,tone,rank:rank[tone],billed,noPrepayment,
  problem:tone==='critical'?'Почти закончился остаток':tone==='warning'?'Маленький остаток':null};
}
export function sortedBalances(ops,now=Date.now(),transportError=false){
 return (ops?.balances||[]).map(b=>balanceView(b,ops,now,transportError)).sort((a,b)=>a.rank-b.rank||(a.unit===b.unit?(a.amount??Infinity)-(b.amount??Infinity):0)||a.title.localeCompare(b.title));
}
export function machineView(m,ops,now=Date.now(),transportError=false){
 const receipt=!transportError&&ops?.fleet?.status==='ok'&&freshAt(ops?.collected_at,now,1800);
 const hostFresh=receipt&&freshAt(m.observed_at,now,1800);
 const active=(m.issues||[]).filter(i=>receipt&&freshAt(i.observed_at,now,i.ttl_seconds)).sort((a,b)=>rank[a.severity]-rank[b.severity]);
 const confirmed=active.filter(i=>i.severity!=='unknown');
 let tone=confirmed[0]?.severity||'unknown';
 let message=confirmed[0]?.text;
 if(!message){
  if(!receipt||!hostFresh)message='Нет свежего замера';
  else if(m.state==='unreachable')message='Нет связи с диагностикой';
  else if(m.state==='not_enrolled')message='Диагностика не подключена';
  else if(m.state==='observed_ok'&&!active.length){message='Без замечаний на замере';tone='ok';}
  else message=active[0]?.text||'Состояние не подтверждено';
 }
 return {...m,tone,message,active,hostFresh,rank:rank[tone]};
}
export function sortedMachines(ops,now=Date.now(),transportError=false){
 return (ops?.fleet?.machines||[]).map(m=>machineView(m,ops,now,transportError)).sort((a,b)=>a.rank-b.rank||a.id.localeCompare(b.id));
}

export const machineCondition=m=>!m.hostFresh?'source:stale':m.active.length?m.active.map(i=>i.code+':'+i.severity).sort().join('|'):'state:'+m.state;

import {freshAt} from './operations-view.mjs';
import {dateLabel,windowLabel} from './account-view.mjs';
const count=n=>Number.isInteger(n)&&n>=0?String(n):'неизвестно';
export function opaque(value){
 let hash=14695981039346656037n;
 for(const char of String(value)){hash^=BigInt(char.codePointAt(0));hash=BigInt.asUintN(64,hash*1099511628211n);}
 return hash.toString(16).padStart(16,'0');
}
const revision=r=>opaque(JSON.stringify([r.tone,r.reason,r.value]));

export function reconcile(previous,records,retired=[]){
 const result=new Map(),present=new Set(records.map(r=>r.id));
 for(const [id,old]of previous)if(!retired.includes(old.entity)&&!present.has(id))result.set(id,{...old,unconfirmed:true});
 for(const r of records){
  const old=previous.get(r.id);
  if(r.state==='clear'||r.state==='retired'||retired.includes(r.entity))continue;
  if(r.state==='unknown'){if(old)result.set(r.id,{...old,unconfirmed:true});continue;}
  result.set(r.id,{...r,revision:revision(r),unconfirmed:false});
 }
 return result;
}

export const compact=(record,seen)=>record.tone!=='critical'&&!record.unconfirmed&&seen.get(record.id)===record.revision;

export function overview(snapshot,accounts,resources,now=Date.now(),transportError=false){
 const records=[],events=[],retired=[];
 const add=r=>records.push({owner:'Вы',value:null,observedAt:null,reason:r.id,evidence:[],...r});
 for(const {account:a,view:v}of accounts){
  const entity='account:'+a.id,name=a.login||a.label,observed=a.source_observed_at||snapshot?.observed_at_utc;
  const authFresh=!transportError&&!snapshot?.cache?.last_error&&freshAt(observed,now,90000);
  add({id:'auth-'+a.id,entity,domain:'subscriptions',title:name+' · доступ',state:v.authorizationIssue?(authFresh?'open':'unknown'):v.fresh?'clear':'unknown',tone:'warning',reason:'authorization',observedAt:observed,
   detail:'Для чтения данных нужна авторизация. Остаток квоты неизвестен.',evidence:[['Источник',(a.source_titles||[]).join(', ')||'Снимок аккаунтов'],['Результат',v.authorizationIssue?'Ошибка доступа':'Свежая ошибка доступа не подтверждена']],next:'Открыть сведения о доступе'});
  if(!v.windows.length)add({id:'quota-missing-'+a.id,entity,domain:'subscriptions',title:name+' · квота неизвестна',state:'unknown',tone:'unknown',observedAt:a.quota?.observed_at,detail:'В источнике нет окон квоты. Отсутствие измерения не означает свободный лимит.',evidence:[['Окна квоты','Не получены']],next:'Открыть сведения о квоте'});
  for(const w of v.windows){
   const measured=!transportError&&w.state==='observed',tone=w.remaining<10?'critical':'warning';
   add({id:'quota-'+a.id+'-'+w.slot+'-'+w.window_minutes,entity,domain:'subscriptions',title:name+' · '+windowLabel(w.window_minutes),state:measured?(w.remaining<25?'open':'clear'):'unknown',tone,reason:'quota',value:measured?w.remaining:null,observedAt:a.quota?.observed_at,
    detail:measured?'Осталось '+Math.round(w.remaining)+'%.':'Нет подтверждённого остатка.',evidence:[['Остаток',measured?String(w.remaining)+'%':'Неизвестно'],['Окно',windowLabel(w.window_minutes)],['Сброс',w.reset_at?dateLabel(w.reset_at):'Неизвестен']],next:'Посмотреть квоту'});
   if(measured&&Number.isFinite(Date.parse(w.reset_at)))events.push({id:'reset-'+a.id+'-'+w.slot,title:'Сброс: '+name+' · '+windowLabel(w.window_minutes),at:w.reset_at,kind:'Ожидаемый сброс квоты',source:'Последний замер квоты',observedAt:a.quota?.observed_at});
  }
 }
 if(!transportError&&!snapshot?.cache?.stale&&snapshot?.inventory?.complete===true){
  for(const a of snapshot.accounts||[])if(a.disabled===true)retired.push('account:'+a.id);
 }
 for(const b of resources.balances){
  add({id:'balance-'+b.id,domain:'balances',title:b.title+' · баланс',state:b.tone==='unknown'?'unknown':['critical','warning'].includes(b.tone)?'open':'clear',tone:b.tone,reason:'balance',value:b.billed?null:b.amount,observedAt:b.source_at,
   detail:b.problem||'Сведения о балансе',evidence:[['Значение',b.amount===null?'Неизвестно':String(b.amount)+' '+b.unit],['Тип',b.billed?'Начислено за период':b.noPrepayment?'Предоплаты нет':'Остаток'],['Последняя проверка',dateLabel(b.observed_at)]],next:'Открыть баланс'});
 }
 for(const m of resources.machines){
  add({id:'machine-'+m.id,domain:'machines',title:m.id==='applications'?'Приложения и резервные копии':m.id,state:m.tone==='ok'?'clear':['critical','warning'].includes(m.tone)?'open':'unknown',tone:m.tone,reason:m.message||'machine',value:m.hostFresh?m.metrics?.disk_free_percent:null,owner:'Ответственный не подтверждён',observedAt:m.active?.[0]?.observed_at||m.observed_at,
   detail:m.message,evidence:[['Источник','Сохранённые проверки Hermes'],['Результат',m.message],['Актуальность машины',m.hostFresh?'Свежий замер':'Нет свежего замера машины']],next:'Открыть проверку'});
 }
 for(const r of resources.integrated){
  const observed=freshAt(r.observed_at,now,90000)&&!transportError;
  const measurements=r.kind==='account'?[r.weekly_remaining,r.five_hour_remaining]:[r.value];
  add({id:'integration-'+r.key,domain:r.page,title:r.title,state:observed&&['critical','warning'].includes(r.tone)?'open':r.current&&r.tone==='ok'?'clear':'unknown',tone:r.tone,reason:JSON.stringify([r.problem||'integration',...measurements]),observedAt:r.observed_at,detail:r.problem||'Сведения интеграции',evidence:[['Источник',r.source],['Наблюдение',dateLabel(r.observed_at)],...(r.kind==='account'?[['Неделя',r.weekly_remaining==null?'Неизвестно':r.weekly_remaining+'%'],['5 часов',r.five_hour_remaining==null?'Неизвестно':r.five_hour_remaining+'%']]:r.kind==='balance'?[['Значение',r.value==null?'Неизвестно':r.value+' '+(r.unit||'')]]:[])],next:'Открыть источник'});
 }
 const data=snapshot?.cockpit,c=data?.court,cockpitFresh=!transportError&&freshAt(data?.collected_at,now,120);
 const courtFresh=cockpitFresh&&freshAt(c?.observed_at,now,129600);
 const courtFacts=c?[
  ['Общий охват',c.status],['Состояние поиска',c.search_status],['Непроверенных записей',count(c.unverified)],['Перенесено из прошлых наблюдений',count(c.carried_forward)],['Дел КАД в сохранённом состоянии',count(c.known_cases)],
  ['Область отдельной квитанции',c.receipt_scope],['Результат отдельной квитанции',c.receipt_status],['Изменений в области этой квитанции',count(c.changes)],['Отмечено сборщиком как важное',count(c.important)],['Дата отдельной квитанции',dateLabel(c.receipt_observed_at)],
  ['Будущие заседания',c.confirmed_dates_available?'Есть структурированные подтверждения':'Подтверждённый список недоступен']]:[['Источник','Не подключён или не прошёл проверку']];
 add({id:'court-coverage',domain:'courts',title:'Проверка судов: '+(c?.status==='ok'?'охват подтверждён':'охват неполный'),state:courtFresh?(c.status==='ok'?'clear':c.status==='unavailable'?'unknown':'open'):'unknown',tone:'warning',reason:JSON.stringify(['court-coverage',c?.status,c?.search_status,c?.unverified,c?.carried_forward]),owner:'Ответственный не подтверждён',observedAt:c?.observed_at,
  detail:'Непроверено: '+count(c?.unverified)+' · перенесено: '+count(c?.carried_forward)+'. Это полнота данных, не оценка юридического риска.',evidence:courtFacts,next:'Открыть судебную сводку'});
 const tasks=(data?.tasks||[]).map(t=>({...t,active:cockpitFresh&&freshAt(t.observed_at,now,120)&&['running','claimed'].includes(t.state)&&t.liveness==='verified',fresh:cockpitFresh&&freshAt(t.observed_at,now,120)})).sort((a,b)=>Number(b.active)-Number(a.active)||(Date.parse(b.claimed_at)||0)-(Date.parse(a.claimed_at)||0));
 const nextRuns=new Set();
 for(const t of tasks){
  if(t.state==='failed'||t.state==='completed')add({id:'job-result-'+(t.job_key||t.id)+'-'+t.origin,domain:'hermes',title:t.label+' · '+(t.origin==='scheduled'?'плановый запуск':'ручной запуск'),state:t.fresh?(t.state==='failed'?'open':'clear'):'unknown',tone:'warning',reason:'execution-failed-'+t.id,owner:'Профиль '+t.profile,observedAt:t.finished_at||t.observed_at,detail:'Сохранён результат процесса: '+(t.state==='failed'?'ошибка':'завершён')+'. Ручной повтор не заменяет результат планового запуска.',evidence:[['Профиль',t.profile],['Источник запуска',t.origin],['Результат',t.state],['Завершение',dateLabel(t.finished_at)]],next:'Посмотреть результат запуска'});
  if(t.enabled===true&&t.fresh&&t.next_run_at&&!nextRuns.has(t.job_key||t.id)){
   nextRuns.add(t.job_key||t.id);events.push({id:'job-next-'+(t.job_key||t.id),title:t.label,at:t.next_run_at,kind:'Запланирован запуск · '+t.profile,source:'Сохранённое расписание Hermes',observedAt:t.observed_at});
  }
 }
 for(const e of data?.events||[])if(cockpitFresh&&e.confirmed&&e.date_kind!=='inferred'&&freshAt(e.observed_at,now,129600))events.push({id:e.id,title:e.title,at:e.at,kind:{hearing:'Заседание',confirmed_deadline:'Подтверждённый срок',publication:'Дата публикации'}[e.date_kind],source:e.source,observedAt:e.observed_at,dateOnly:/^\d{4}-\d{2}-\d{2}$/.test(e.at)});
 return {records,retired,tasks,activeTasks:tasks.filter(t=>t.active),cockpitFresh,courtFresh,courtFacts,court:c,profiles:data?.profiles||[],
  events:events.filter(e=>{
   if(e.dateOnly){const day=ms=>new Date(ms+3*3600000).toISOString().slice(0,10);return e.at>=day(now)&&e.at<=day(now+7*86400000);}
   const at=Date.parse(e.at);return Number.isFinite(at)&&at>=now&&at<=now+7*86400000;
  }).sort((a,b)=>a.at.localeCompare(b.at))};
}

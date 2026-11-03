import {freshAt,machineCondition} from './operations-view.mjs';
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
   add({id:'quota-'+a.id+'-'+w.slot+'-'+w.window_minutes,entity,domain:'subscriptions',title:name+' · '+windowLabel(w.window_minutes),state:measured?(w.remaining<25?'open':'clear'):'unknown',tone,reason:'quota',condition_key:'quota:'+(measured?(w.remaining<10?'critical':w.remaining<25?'low':'normal'):'unknown'),value:measured?w.remaining:null,observedAt:a.quota?.observed_at,
    detail:measured?'Осталось '+Math.round(w.remaining)+'%.':'Нет подтверждённого остатка.',evidence:[['Остаток',measured?String(w.remaining)+'%':'Неизвестно'],['Окно',windowLabel(w.window_minutes)],['Сброс',w.reset_at?dateLabel(w.reset_at):'Неизвестен']],next:'Посмотреть квоту'});
   if(measured&&Number.isFinite(Date.parse(w.reset_at)))events.push({id:'reset-'+a.id+'-'+w.slot,title:'Сброс: '+name+' · '+windowLabel(w.window_minutes),at:w.reset_at,kind:'Ожидаемый сброс квоты',source:'Последний замер квоты',observedAt:a.quota?.observed_at});
  }
 }
 if(!transportError&&!snapshot?.cache?.stale&&snapshot?.inventory?.complete===true){
  for(const a of snapshot.accounts||[])if(a.disabled===true)retired.push('account:'+a.id);
 }
 for(const b of resources.balances){
  add({id:'balance-'+b.id,domain:'balances',title:b.title+' · баланс',state:b.tone==='unknown'?'unknown':['critical','warning'].includes(b.tone)?'open':'clear',tone:b.tone,reason:'balance',condition_key:'balance:'+b.tone+':'+(b.problem||''),value:b.billed?null:b.amount,observedAt:b.source_at,
   detail:b.problem||'Сведения о балансе',evidence:[['Значение',b.amount===null?'Неизвестно':String(b.amount)+' '+b.unit],['Тип',b.billed?'Начислено за период':b.noPrepayment?'Предоплаты нет':'Остаток'],['Последняя проверка',dateLabel(b.observed_at)]],next:'Открыть баланс'});
 }
 for(const m of resources.machines){
  add({id:'machine-'+m.id,domain:'machines',title:m.id==='applications'?'Приложения и резервные копии':m.id,state:m.tone==='ok'?'clear':['critical','warning'].includes(m.tone)?'open':'unknown',tone:m.tone,reason:m.message||'machine',value:m.hostFresh?m.metrics?.disk_free_percent:null,condition_key:machineCondition(m),owner:'Hermes · ops',observedAt:m.active?.[0]?.observed_at||m.observed_at,
   detail:m.message,evidence:[['Источник','Сохранённые проверки Hermes'],['Результат',m.message],['Актуальность машины',m.hostFresh?'Свежий замер':'Нет свежего замера машины']],next:'Открыть проверку'});
 }
 for(const r of resources.integrated){
  const observed=freshAt(r.observed_at,now,90000)&&!transportError;
  const measurements=r.kind==='account'?[r.weekly_remaining,r.five_hour_remaining]:[r.value];
  add({id:'integration-'+r.key,domain:r.page,title:r.title,state:observed&&['critical','warning'].includes(r.tone)?'open':r.current&&r.tone==='ok'?'clear':'unknown',tone:r.tone,reason:JSON.stringify([r.problem||'integration',...measurements]),condition_key:'integration:'+r.tone+':'+(r.current?'current':'unknown')+':'+(r.problem||''),observedAt:r.observed_at,detail:r.problem||'Сведения интеграции',evidence:[['Источник',r.source],['Наблюдение',dateLabel(r.observed_at)],...(r.kind==='account'?[['Неделя',r.weekly_remaining==null?'Неизвестно':r.weekly_remaining+'%'],['5 часов',r.five_hour_remaining==null?'Неизвестно':r.five_hour_remaining+'%']]:r.kind==='balance'?[['Значение',r.value==null?'Неизвестно':r.value+' '+(r.unit||'')]]:[])],next:'Открыть источник'});
 }
 const data=snapshot?.cockpit,c=data?.court,cockpitFresh=!transportError&&freshAt(data?.collected_at,now,120);
 const coverageFresh=!transportError&&freshAt(data?.collected_at,now,1800);
 const courtFresh=coverageFresh&&freshAt(c?.observed_at,now,129600);
 const courtFacts=c?[
  ['Общий охват',c.status],['Состояние поиска',c.search_status],['Непроверенных записей',count(c.unverified)],['Перенесено из прошлых наблюдений',count(c.carried_forward)],['Дел КАД в сохранённом состоянии',count(c.known_cases)],
  ['Область отдельной квитанции',c.receipt_scope],['Результат отдельной квитанции',c.receipt_status],['Изменений в области этой квитанции',count(c.changes)],['Отмечено сборщиком как важное',count(c.important)],['Дата отдельной квитанции',dateLabel(c.receipt_observed_at)],
  ['Будущие заседания',c.confirmed_dates_available?'Есть структурированные подтверждения':'Подтверждённый список недоступен']]:[['Источник','Не подключён или не прошёл проверку']];
 add({id:'court-coverage',domain:'courts',title:'Проверка судов: '+(c?.status==='ok'?'охват подтверждён':'охват неполный'),state:courtFresh?(c.status==='ok'?'clear':c.status==='unavailable'?'unknown':'open'):'unknown',tone:'warning',reason:JSON.stringify(['court-coverage',c?.status,c?.search_status,c?.unverified,c?.carried_forward]),owner:'Ответственный не подтверждён',observedAt:c?.observed_at,
  detail:'Непроверено: '+count(c?.unverified)+' · перенесено: '+count(c?.carried_forward)+'. Это полнота данных, не оценка юридического риска.',evidence:courtFacts,next:'Открыть судебную сводку'});
 const tasks=(data?.tasks||[]).map(t=>({...t,active:cockpitFresh&&freshAt(t.observed_at,now,120)&&['running','claimed'].includes(t.state)&&t.liveness==='verified',fresh:coverageFresh&&freshAt(t.observed_at,now,1800)})).sort((a,b)=>Number(b.active)-Number(a.active)||(Date.parse(b.claimed_at)||0)-(Date.parse(a.claimed_at)||0));
 const nextRuns=new Set();
 for(const t of tasks){
  if(t.state==='failed'||t.state==='completed')add({id:'job-result-'+(t.job_key||t.id)+'-'+t.origin,domain:'hermes',title:t.label+' · '+(t.origin==='scheduled'?'плановый запуск':'ручной запуск'),state:t.fresh?(t.state==='failed'?'open':'clear'):'unknown',tone:'warning',reason:'execution-failed-'+t.id,condition_key:'execution:'+t.id,owner:'Профиль '+t.profile,observedAt:t.finished_at||t.observed_at,detail:'Сохранён результат процесса: '+(t.state==='failed'?'ошибка':'завершён')+'. Ручной повтор не заменяет результат планового запуска.',evidence:[['Профиль',t.profile],['Источник запуска',t.origin],['Результат',t.state],['Завершение',dateLabel(t.finished_at)]],next:'Посмотреть результат запуска'});
  if(t.enabled===true&&t.fresh&&t.next_run_at&&!nextRuns.has(t.job_key||t.id)){
   nextRuns.add(t.job_key||t.id);events.push({id:'job-next-'+(t.job_key||t.id),title:t.label,at:t.next_run_at,kind:'Запланирован запуск · '+t.profile,source:'Сохранённое расписание Hermes',observedAt:t.observed_at});
  }
 }
 for(const e of data?.events||[])if(coverageFresh&&e.confirmed&&e.date_kind!=='inferred'&&freshAt(e.observed_at,now,129600))events.push({id:e.id,title:e.title,at:e.at,kind:{hearing:'Заседание',confirmed_deadline:'Подтверждённый срок',publication:'Дата публикации'}[e.date_kind],source:e.source,observedAt:e.observed_at,dateOnly:/^\d{4}-\d{2}-\d{2}$/.test(e.at)});
 return {records,retired,tasks,activeTasks:tasks.filter(t=>t.active),cockpitFresh,coverageFresh,courtFresh,courtFacts,court:c,profiles:data?.profiles||[],
  events:events.filter(e=>{
   if(e.dateOnly){const day=ms=>new Date(ms+3*3600000).toISOString().slice(0,10);return e.at>=day(now)&&e.at<=day(now+7*86400000);}
   const at=Date.parse(e.at);return Number.isFinite(at)&&at>=now&&at<=now+7*86400000;
  }).sort((a,b)=>{
   const calendar=e=>e.dateOnly?e.at:new Date(Date.parse(e.at)+3*3600000).toISOString();
   return calendar(a).localeCompare(calendar(b));
  })};
}


export const workActions={diagnose:'Разбор причины',check_access:'Проверка существующего доступа',inspect_disk:'Анализ занятого места',inspect_service:'Диагностика служб',inspect_backup:'Проверка резервных копий',prepare_fix:'Подготовка исправления',test_fix:'Проверка исправления',verify_recovery:'Проверка восстановления',wait_supervisor:'Проверка штатного восстановления',wait_reset:'Ожидание сброса квоты',check_balance:'Проверка баланса',check_job:'Разбор неудачного запуска',check_source:'Проверка источника данных'};
export const workBlockers={none:null,no_access:'Нет подтверждённого доступа',no_safe_procedure:'Нужна проверенная процедура исправления',active_work:'На машине идёт работа',awaiting_source:'Нет свежих данных источника',upstream:'Внешний сервис недоступен',execution_failed:'Запуск завершился с ошибкой',login_required:'Нужен вход владельца',payment_required:'Нужна оплата',owner_approval:'Нужно решение владельца'};
export function incidentView(record,work,now=Date.now(),transportError=false){
 const key=record.condition_key||JSON.stringify([record.state,record.reason,record.value]);
 const item=work?.status==='ok'?work.items.find(w=>w.record_id===record.id&&w.condition_key===key&&(w.source_state===record.state||record.unconfirmed&&w.source_state==='unknown')):null;
 if(!item)return {lane:'hermes',label:'Передача ещё не подтверждена',action:null,blocker:'Нет актуальной записи ops по этой проблеме',item:null};
 const action=workActions[item.action],blocker=workBlockers[item.blocker];
 if(transportError||!freshAt(work.observed_at,now,1800))return {lane:'hermes',label:'Последняя запись · текущее состояние не подтверждено',action,blocker,item,observedAt:work.observed_at};
 if(item.state==='queued')return {lane:'hermes',label:'Передано ops · ждёт разбора',action:null,blocker:null,item,observedAt:work.observed_at};
 if(item.state==='needs_user'&&record.state!=='clear'&&!record.unconfirmed&&freshAt(item.source_at,now,1800)&&['login_required','payment_required','owner_approval'].includes(item.blocker)&&item.decision)return {lane:'owner',label:'Нужно ваше решение',action,blocker,item,observedAt:work.observed_at};
 if(item.state==='resolved'&&item.source_state==='clear')return {lane:'hermes',label:'Восстановление проверено',action,blocker:null,item,observedAt:work.observed_at};
 if(item.state==='accepted'){
  const live=item.execution_liveness==='verified'&&['claimed','running'].includes(item.execution_state)&&freshAt(work.observed_at,now,120);
  return {lane:'hermes',label:live?(item.actor==='infra-dev'?'infra-dev · владелец на связи':'В работе · процесс подтверждён'):(['completed','failed'].includes(item.execution_state)||item.execution_liveness==='not_live')?'Запуск остановился без итога по проблеме':'Текущая работа не подтверждена',action,blocker:live?null:item.execution_state==='failed'?'Ошибка исполнения':blocker,item,observedAt:work.observed_at};
 }
 return {lane:'hermes',label:item.source_state==='clear'?'В новом замере проблема не видна':item.state==='needs_user'?'Нужно перепроверить запрос к владельцу':item.actor==='infra-dev'?'infra-dev · остановился':'Остановился · ожидание',action,blocker,item,observedAt:work.observed_at};
}

export function maintenanceWork(record,work,now=Date.now(),transportError=false){
 if(record.state!=='clear'||work?.status!=='ok')return null;
 const item=work.items.find(w=>w.record_id===record.id&&w.source_state==='clear'&&['accepted','waiting'].includes(w.state));
 if(!item)return null;
 // A healthy source can coexist with ongoing preparation; this is activity, not a new fault.
 const stage=incidentView({...record,condition_key:item.condition_key},work,now,transportError);
 if(item.state==='waiting'&&!transportError&&freshAt(work.observed_at,now,1800))stage.label=(item.actor||'ops')+' · ожидание';
 stage.active=item.state==='accepted'&&!transportError&&freshAt(work.observed_at,now,120)&&item.execution_liveness==='verified'&&['claimed','running'].includes(item.execution_state);
 return stage;
}

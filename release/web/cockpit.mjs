import {overview,reconcile,compact,opaque,incidentView,maintenanceWork,workSummary} from './cockpit-view.mjs';
import {dateLabel,relativeTime} from './account-view.mjs';
import {machineAction} from './operations.mjs';
const $=id=>document.getElementById(id);
const el=(tag,text,cls)=>{const n=document.createElement(tag);if(text!=null)n.textContent=text;if(cls)n.className=cls;return n;};
const domains={courts:'Суды',subscriptions:'Аккаунты',balances:'Балансы',machines:'Машины',hermes:'Hermes'};
const words={ok:'проверено',partial:'частично',error:'ошибка',unavailable:'недоступно',complete:'полный',incomplete:'неполный',unknown:'неизвестно',courts:'суды',kad_metadata:'метаданные КАД',kad:'КАД',scheduled:'плановый',manual:'ручной',completed:'процесс завершён',failed:'ошибка процесса',running:'идёт по журналу',claimed:'принят по журналу',planned:'запланирован',paused:'приостановлен'};
const word=value=>words[value]||value;
export function displayTitle(title){
 const labels={'Daily safe scratch housekeeping':'Уборка временных файлов','Court — daily arbitration update':'Обновление судебных дел','Plane task follow-through':'Контроль задач','Hermes core update acceptance':'Проверка обновления Hermes'};
 for(const [name,label] of Object.entries(labels))if(title===name||title.startsWith(name+' ·'))return label+title.slice(name.length);
 return title;
}
export function issueAction(record){
 if(record.work)return record.work.lane==='owner'?record.work.item.decision:null;
 if(record.unconfirmed)return 'Сначала проверить свежие данные о проблеме.';
 if(record.recommendation)return record.recommendation;
 if(record.state==='unknown')return 'Проверить доступ к источнику и время последнего замера.';
 if(record.state!=='open')return null;
 if(record.reason==='authorization')return 'Войти в аккаунт и обновить доступ к данным.';
 if(record.reason==='balance'&&Number.isFinite(record.value)&&record.value>=0)return 'Пополнить баланс сервиса.';
 if(record.reason==='quota'&&Number.isFinite(record.value)&&record.value>=0&&record.value<25)return 'Дождаться сброса квоты или выбрать другой аккаунт.';
 if(record.id==='court-coverage')return 'Открыть судебную сводку и проверить пробелы охвата.';
 if(record.domain==='hermes')return 'Открыть результат запуска и выяснить причину ошибки.';
 return null;
}
const seenStorage='cockpit-seen-v1';
let active=new Map(),registry=new Map(),seen=new Map(),returnTo={hash:'#overview',id:null},pendingFocus=null;
try{
 const stored=JSON.parse(sessionStorage.getItem(seenStorage)||'[]');
 if(Array.isArray(stored))seen=new Map(stored.slice(-200).filter(r=>Array.isArray(r)&&r.length===2&&r.every(v=>typeof v==='string'&&/^[a-f0-9]{16}$/.test(v))));
}catch{/* Unavailable browser storage leaves viewed items expanded. */}
function saveSeen(){
 try{sessionStorage.setItem(seenStorage,JSON.stringify([...seen]));}catch{/* Viewing still works without storage. */}
}
function markSeen(record){
 seen.delete(opaque(record.id));seen.set(opaque(record.id),record.revision);
 if(seen.size>200)seen.delete(seen.keys().next().value);
 saveSeen();
}
function openLink(record,label){
 const a=el('a',label||record.next||'Посмотреть доказательства','cockpit-action');
 a.href='#evidence/'+opaque(record.id);
 a.addEventListener('click',event=>{returnTo={hash:location.hash||'#overview',id:event.currentTarget.closest('.cockpit-row')?.id};if(record.revision)markSeen(record);});
 return a;
}
function row(record,now,{small=false,scope='issue'}={}){
 const article=el('article',null,'cockpit-row '+(record.tone||'unknown')+(small?' is-seen':''));article.id='cockpit-row-'+opaque(record.id)+'-'+scope;
 if(record.work||record.phase)article.dataset.workPhase=record.work?.phase||record.phase;
 const when=el('div',record.when|| (record.observedAt?relativeTime(record.observedAt,now):'Нет замера'),'cockpit-when');
 const body=el('div',null,'cockpit-body');
 body.append(el('span',record.badge||(record.unconfirmed?'Не решено · текущий статус неизвестен':record.work?.label|| (record.tone==='critical'?'Важно · не решено':record.tone==='unknown'?'Нет подтверждения':small?'Просмотрено · не решено':'Требует внимания')),'cockpit-tag '+(record.tone||'unknown')));
 body.append(el('h3',displayTitle(record.title)));
 if(!small){body.append(el('p',record.detail));if(record.domain)body.append(el('p',(record.owner||'Ответственный не подтверждён')+' · '+(domains[record.domain]||record.domain),'muted small'));}
 const progress=record.work||record.progress;
 if(record.unconfirmed&&record.work&&!small)body.append(el('p',record.work.label,'small'));
 if(progress?.action&&!small)body.append(el('p','Последний этап: '+progress.action+(progress.at?' · '+relativeTime(progress.at,now):''),'small'));
 if(record.work?.item&&!small)body.append(el('p','Отметка Hermes: '+relativeTime(record.work.item.updated_at,now),'muted small'));
 if(progress?.blocker&&!small)body.append(el('p',progress.blocker,'small'));
 if(record.work?.history&&!small){const h=record.work.history;body.append(el('p','Ранее: '+h.action+' · '+relativeTime(h.at,now)+(h.blocker?' · '+h.blocker:''),'muted small'));}
 if(!small&&record.work?.preparation)body.append(el('p',record.work.preparation.label+' · '+relativeTime(record.work.preparation.at,now),'small'));
 const action=issueAction(record);if(action&&!small)body.append(el('p','Что сделать: '+action,'small'));
 body.append(openLink(record));article.append(when,body);return article;
}
function table(pairs){
 const dl=el('dl',null,'cockpit-facts');
 for(const [label,value]of pairs){const pair=el('div');pair.append(el('dt',label),el('dd',value==null?'Неизвестно':word(String(value))));dl.append(pair);}
 return dl;
}
function taskRecord(task,now,publishedAt){
 const state=task.active?'Выполняется · процесс подтверждён':!task.fresh?'Старый снимок · текущее состояние неизвестно':({queued:'В очереди · плановый запуск',waiting:'Ожидание · расписание приостановлено',interrupted:task.state==='failed'?'Ошибка процесса · результат не принят':'Процесс остановился · итог не подтверждён',result:'Процесс завершён · результат требует проверки'}[task.phase]||'Выполнение не подтверждено');
 const progress=task.progress_at?{action:'Отметка прогресса без описания операции',at:task.progress_at}:task.finished_at?{action:'Завершение процесса',at:task.finished_at}:task.started_at?{action:'Начало процесса',at:task.started_at}:task.claimed_at?{action:'Запуск принят',at:task.claimed_at}:{action:'Операция не записана',at:null};
 progress.blocker=task.phase==='unconfirmed'?'Нет свежего подтверждения процесса':task.phase==='interrupted'?'Запуск остановился; предметный итог не подтверждён':task.phase==='waiting'?'Плановые запуски приостановлены':task.phase==='queued'?'Ожидает планового запуска':task.phase==='result'?'Завершение процесса не доказывает восстановление':null;
 return {id:'task-'+task.id,domain:'hermes',title:task.label,badge:state,phase:task.phase,progress,tone:task.state==='failed'?'warning':'unknown',observedAt:task.observed_at,
 detail:(task.origin==='scheduled'?'Плановый':task.origin==='manual'?'Ручной':'Неизвестный')+' запуск · '+state,
 owner:'Профиль '+task.profile,next:'Посмотреть запись исполнения',evidence:[['Источник состояния','Журнал исполнений Hermes'],['Профиль',task.profile],['Источник запуска',word(task.origin)],['Состояние процесса',state],['Принят',dateLabel(task.claimed_at)],['Начало',dateLabel(task.started_at)],['Завершение',dateLabel(task.finished_at)],['Последняя отметка прогресса',task.progress_at?dateLabel(task.progress_at):'Не записана; это само по себе не ошибка'],['Следующий плановый запуск',task.next_run_at?dateLabel(task.next_run_at):'Неизвестен'],['Контрольная точка текущей работы','Журнал не содержит этап предметной задачи'],['Область результата','Статус процесса не доказывает полноту проверки данных'],['Время чтения журнала',dateLabel(task.observed_at)],['Время публикации сводки',dateLabel(publishedAt)]]};
}
function evidence(now){
 const root=$('evidence-content'),key=location.hash.split('/')[1];
 if(!location.hash.startsWith('#evidence/'))return;
 const r=registry.get(key),back=el('a','← Назад к списку','cockpit-action');back.id='evidence-back';back.href=returnTo.hash.startsWith('#evidence')?'#overview':returnTo.hash;
 back.addEventListener('click',()=>{pendingFocus=returnTo.id;});
 root.replaceChildren(back);
 if(!r){root.append(el('h2','Запись сейчас недоступна'),el('p','Вернитесь к списку: источник мог измениться или запись отсутствует в этой копии.'));return;}
 if(r.revision)markSeen(r);
 const title=el('h2',displayTitle(r.title));title.tabIndex=-1;root.append(title);
 if(displayTitle(r.title)!==r.title)root.append(el('p','Название в источнике: '+r.title,'muted small'));
 if(r.unconfirmed)root.append(el('p','Ранее проблема была подтверждена. Сейчас данных для проверки её состояния нет.','notice'));
 root.append(el('p',r.detail),table([['Ответственный',r.owner||'Не подтверждён'],['Время наблюдения',r.observedAt?dateLabel(r.observedAt):'Неизвестно'],...r.evidence]));
 if(r.work){root.append(table([['Источник состояния','Checkpoint ops / сохранённый handoff'],['Передача',r.work.label],['Последний этап',r.work.action],['Остановка',r.work.blocker],['Отметка Hermes',r.work.item?dateLabel(r.work.item.updated_at):null],['Запуск ops на замере',r.work.item?.execution_state],['Время чтения записи ops',r.work.observedAt?dateLabel(r.work.observedAt):null],['Время публикации сводки',dateLabel(r.publishedAt)],['Задача',r.work.item?.task_ref],['Область подтверждения процесса',r.work.item?.actor==='infra-dev'?'Сведения о процессе владельца ops; этап infra-dev — из сохранённого handoff':'Живой процесс не доказывает выполнение конкретной операции']]));}
 if(r.work?.history)root.append(table([['Историческая операция',r.work.history.action],['Историческая блокировка',r.work.history.blocker],['Время исторической записи',dateLabel(r.work.history.at)],['Согласованность','Запись относится к другому состоянию источника; активность и запрос владельцу не подтверждены']]));
 if(r.work?.preparation)root.append(table([['Проверка плана',r.work.preparation.label],['Проверено',dateLabel(r.work.preparation.at)],['Ограничение','Проверка плана не подтверждает очистку или восстановление машины.']]));
 const action=issueAction(r);if(action)root.append(el('p','Что сделать: '+action));
 if(r.domain&&domains[r.domain]){const source=el('a','Открыть раздел «'+domains[r.domain]+'»','cockpit-action');source.href='#'+r.domain;root.append(source);}
 root.append(el('p','Просмотр не означает решение. Новая или изменившаяся проблема появляется снова; важная остаётся наверху. История до открытия этой вкладки не восстанавливается.','muted small'));
 if(document.activeElement?.closest('#evidence-content')===null)title.focus({preventScroll:true});
}
export function renderCockpit(snapshot,accounts,resources,now,transportError){
 const view=overview(snapshot,accounts,resources,now,transportError);
 const machines=new Map(resources.machines.map(m=>['machine-'+m.id,m]));
 for(const r of view.records)if(machines.has(r.id))r.recommendation=machineAction(machines.get(r.id));
 const integrations=new Map(resources.integrated.map(r=>['integration-'+r.key,r]));
 for(const r of view.records){const i=integrations.get(r.id);if(r.state==='open'&&i&&!i.current&&i.tone==='warning')r.recommendation='Войти в сервис и обновить доступ к данным.';}
 let cleared=false;
 for(const r of [...view.records,...active.values()])if(r.state==='clear'||view.retired.includes(r.entity))cleared=seen.delete(opaque(r.id))||cleared;
 if(cleared)saveSeen();
 active=reconcile(active,view.records,view.retired);
 const previousRegistry=registry;
 registry=new Map(view.records.map(r=>[opaque(r.id),r]));for(const r of active.values())registry.set(opaque(r.id),r);
 for(const r of active.values()){r.work=incidentView(r,snapshot?.cockpit?.work,now,transportError);r.publishedAt=snapshot?.cockpit?.collected_at;r.owner=r.work.lane==='owner'?'Вы':r.work.item?.actor==='infra-dev'?'Hermes · infra-dev':'Hermes · ops';}
 const seenForRows=new Map([...active.values()].map(r=>[r.id,seen.get(opaque(r.id))]));
 const ordered=[...active.values()].sort((a,b)=>Number(b.tone==='critical')-Number(a.tone==='critical')||Number(b.unconfirmed)-Number(a.unconfirmed));
 const decisions=ordered.filter(r=>r.work.lane==='owner');
 const expanded=decisions.filter(r=>!compact(r,seenForRows)),viewed=decisions.filter(r=>compact(r,seenForRows));
 const delegated=ordered.filter(r=>r.work.lane==='hermes');
 const gaps=view.records.filter(r=>r.state==='unknown'&&!active.has(r.id));
 for(const previous of previousRegistry.values())if(previous.work?.maintenance&&!registry.has(opaque(previous.id))&&!view.retired.includes(previous.entity)){
  const retained={...previous,state:'unknown',tone:'unknown',unconfirmed:true};gaps.push(retained);registry.set(opaque(retained.id),retained);
 }
 for(const r of gaps){r.work=incidentView({...r,work:previousRegistry.get(opaque(r.id))?.work},snapshot?.cockpit?.work,now,transportError);r.publishedAt=snapshot?.cockpit?.collected_at;r.owner=r.work.lane==='owner'?'Вы':r.work.item?.actor==='infra-dev'?'Hermes · infra-dev':'Hermes · ops';}
 for(const r of gaps.filter(r=>r.work.lane==='owner')){decisions.push(r);expanded.push(r);}
 delegated.push(...gaps.filter(r=>(r.work.item||r.work.history)&&r.work.lane==='hermes'));
 for(const r of view.records){
  const previous=previousRegistry.get(opaque(r.id)),work=maintenanceWork({...r,work:previous?.work},snapshot?.cockpit?.work,now,transportError);
  if(work){const activity={...r,tone:'ok',publishedAt:snapshot?.cockpit?.collected_at,owner:work.item?'Hermes · '+(work.item.actor||'ops'):previous.owner,work,detail:'На замере без замечаний. Результат и подготовка Hermes учитываются отдельно.'};if(work.active)delegated.unshift(activity);else delegated.push(activity);registry.set(opaque(r.id),activity);}
 }
 const workCounts=workSummary(delegated.map(r=>r.work));
 $('cockpit-coverage').replaceChildren(el('strong',`${decisions.length} решений для вас · Задачи Hermes — ${workCounts} · ${gaps.length} пробелов`),el('p',view.coverageFresh?'Обновление сводки: 15 мин · актуальность каждого источника — в доказательствах.':'Нет свежего чтения Court / Hermes. Активная работа не подтверждена.','small'));
 $('cockpit-count').textContent=expanded.length+' записей';
 $('cockpit-decisions').replaceChildren(...expanded.map(r=>row(r,now)));
 if(!expanded.length)$('cockpit-decisions').append(el('p',decisions.length?'Остальное просмотрено и остаётся нерешённым ниже.':'Подтверждённых запросов к вам нет. Технические проблемы — в очереди Hermes ниже.','cockpit-empty'));
 $('cockpit-seen').hidden=!viewed.length;$('cockpit-seen-count').textContent='Просмотрено · не решено: '+viewed.length;
 $('cockpit-seen-list').replaceChildren(...viewed.map(r=>row(r,now,{small:true})));
 $('cockpit-unknown-count').textContent='Пробелы в данных: '+gaps.length;$('cockpit-unknown').hidden=!gaps.length;
 $('cockpit-unknown-list').replaceChildren(...gaps.map(r=>row({...r,tone:'unknown',detail:'Нет свежего подтверждения. Откройте источник и время замера.'},now)));
 const events=view.events.map(e=>{
  const record={id:e.id,title:e.title,domain:null,observedAt:e.observedAt,tone:'unknown',badge:e.kind,when:e.dateOnly?e.at:dateLabel(e.at),detail:e.source,evidence:[['Вид даты',e.kind],['Дата',e.dateOnly?e.at+' · время не указано':dateLabel(e.at)],['Источник',e.source]],next:'Посмотреть дату'};
  registry.set(opaque(record.id),record);return row(record,now);
 });
 $('cockpit-work').replaceChildren(...delegated.slice(0,6).map(r=>row(r,now,{scope:'work'})));
 if(delegated.length>6){const more=el('details',null,'cockpit-fold');more.append(el('summary','Ещё задач у Hermes: '+(delegated.length-6)),...delegated.slice(6).map(r=>row(r,now,{scope:'work'})));$('cockpit-work').append(more);}
 $('cockpit-work-count').textContent=workCounts;$('hermes-work-count').textContent=workCounts;
 if(!delegated.length)$('cockpit-work').append(el('p','Нерешённых проблем в очереди не видно. Полнота данных указана отдельно.','cockpit-empty'));
 $('hermes-incidents').replaceChildren(...delegated.map(r=>row(r,now,{scope:'hermes-work'})));
 $('cockpit-events').replaceChildren(...events.slice(0,3));
 if(!events.length)$('cockpit-events').append(el('p','Подтверждённых дат из доступных источников на 7 дней нет. Это не означает отсутствие сроков.','cockpit-empty'));
 if(events.length>3){const more=el('details',null,'cockpit-fold');more.append(el('summary','Ещё дат: '+(events.length-3)),...events.slice(3));$('cockpit-events').append(more);}
 const taskRecords=view.tasks.map(t=>taskRecord(t,now,snapshot?.cockpit?.collected_at));for(const r of taskRecords)registry.set(opaque(r.id),r);
 $('cockpit-active').replaceChildren(...taskRecords.filter(t=>t.phase==='active').map(r=>row(r,now,{scope:'active'})));
 if(!view.activeTasks.length)$('cockpit-active').append(el('p','Подтверждённых активных исполнений нет. Это не доказательство простоя: журнал может быть неполным.','cockpit-empty'));
 $('hermes-tasks').replaceChildren(...taskRecords.map(r=>row(r,now,{scope:'tasks'})));
 $('hermes-task-count').textContent=workSummary(view.tasks);
 if(!taskRecords.length)$('hermes-tasks').append(el('p','Записи исполнений недоступны.','cockpit-empty'));
 $('hermes-coverage').textContent=(view.coverageFresh?'Снимок журналов получен. ':'Снимок журналов устарел. ')+view.profiles.map(p=>p.id+': '+word(p.status)+(p.stored_jobs==null?'':' · '+p.stored_jobs+' заданий')).join(' / ');
 $('court-summary').replaceChildren(el('h2',view.courtFresh&&view.court?.status==='ok'?'Охват подтверждён':'Суды: охват неполный'),el('p','Статус отдельного сборщика относится только к указанной области проверки. Он не закрывает пробелы других источников.'));
 if(!view.courtFresh)$('court-summary').append(el('p','Нет свежего подтверждения состояния судов.','notice'));
 $('court-summary').append(table(view.courtFacts),el('p','Заседания и процессуальные сроки появятся только при наличии структурированного подтверждения. По текстовым упоминаниям даты не вычисляются.','muted small'));
 $('cockpit-domains').replaceChildren(...Object.entries(domains).map(([id,title])=>{const a=el('a',null,'cockpit-domain');a.href='#'+id;const n=[...active.values()].filter(r=>r.domain===id).length,u=gaps.filter(r=>r.domain===id).length;a.append(el('strong',title),el('span',n?`${n} нерешённых`:u?`${u} пробелов`:'Открыть данные','small muted'));return a;}));
 evidence(now);
 if(pendingFocus&&!location.hash.startsWith('#evidence/')){
  const id=pendingFocus;pendingFocus=null;
  requestAnimationFrame(()=>{const target=document.getElementById(id);if(target){const fold=target.closest('details');if(fold)fold.open=true;target.tabIndex=-1;target.focus({preventScroll:true});target.scrollIntoView({block:'center'});}});
 }
}

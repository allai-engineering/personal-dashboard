import {overview,reconcile,compact,opaque} from './cockpit-view.mjs';
import {dateLabel,relativeTime} from './account-view.mjs';
const $=id=>document.getElementById(id);
const el=(tag,text,cls)=>{const n=document.createElement(tag);if(text!=null)n.textContent=text;if(cls)n.className=cls;return n;};
const domains={courts:'Суды',subscriptions:'Аккаунты',balances:'Балансы',machines:'Машины',hermes:'Hermes'};
const words={ok:'проверено',partial:'частично',error:'ошибка',unavailable:'недоступно',complete:'полный',incomplete:'неполный',unknown:'неизвестно',courts:'суды',kad_metadata:'метаданные КАД',kad:'КАД',scheduled:'плановый',manual:'ручной',completed:'процесс завершён',failed:'ошибка процесса',running:'идёт по журналу',claimed:'принят по журналу',planned:'запланирован',paused:'приостановлен'};
const word=value=>words[value]||value;
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
 const when=el('div',record.when|| (record.observedAt?relativeTime(record.observedAt,now):'Нет замера'),'cockpit-when');
 const body=el('div',null,'cockpit-body');
 body.append(el('span',record.badge||(record.unconfirmed?'Не решено · текущий статус неизвестен':record.tone==='critical'?'Важно · не решено':record.tone==='unknown'?'Нет подтверждения':small?'Просмотрено · не решено':'Требует внимания'),'cockpit-tag '+(record.tone||'unknown')));
 body.append(el('h3',record.title));
 if(!small){body.append(el('p',record.detail));if(record.domain)body.append(el('p',(record.owner||'Ответственный не подтверждён')+' · '+(domains[record.domain]||record.domain),'muted small'));}
 body.append(openLink(record));article.append(when,body);return article;
}
function table(pairs){
 const dl=el('dl',null,'cockpit-facts');
 for(const [label,value]of pairs){const pair=el('div');pair.append(el('dt',label),el('dd',value==null?'Неизвестно':word(String(value))));dl.append(pair);}
 return dl;
}
function taskRecord(task,now){
 const state=task.active?'Выполняется · процесс подтверждён':!task.fresh?'Старый снимок · текущее состояние неизвестно':['claimed','running'].includes(task.state)?'Выполнение не подтверждено':word(task.state);
 return {id:'task-'+task.id,domain:'hermes',title:task.label,badge:state,tone:task.state==='failed'?'warning':'unknown',observedAt:task.observed_at,
 detail:(task.origin==='scheduled'?'Плановый':task.origin==='manual'?'Ручной':'Неизвестный')+' запуск · '+state,
 owner:'Профиль '+task.profile,next:'Посмотреть запись исполнения',evidence:[['Профиль',task.profile],['Источник запуска',word(task.origin)],['Состояние процесса',state],['Принят',dateLabel(task.claimed_at)],['Начало',dateLabel(task.started_at)],['Завершение',dateLabel(task.finished_at)],['Последняя отметка прогресса',task.progress_at?dateLabel(task.progress_at):'Не записана; это само по себе не ошибка'],['Следующий плановый запуск',task.next_run_at?dateLabel(task.next_run_at):'Неизвестен'],['Контрольная точка текущей работы','Не записана'],['Область результата','Статус процесса не доказывает полноту проверки данных'],['Последнее чтение журнала',relativeTime(task.observed_at,now)]]};
}
function evidence(now){
 const root=$('evidence-content'),key=location.hash.split('/')[1];
 if(!location.hash.startsWith('#evidence/'))return;
 const r=registry.get(key),back=el('a','← Назад к списку','cockpit-action');back.id='evidence-back';back.href=returnTo.hash.startsWith('#evidence')?'#overview':returnTo.hash;
 back.addEventListener('click',()=>{pendingFocus=returnTo.id;});
 root.replaceChildren(back);
 if(!r){root.append(el('h2','Запись сейчас недоступна'),el('p','Вернитесь к списку: источник мог измениться или запись отсутствует в этой копии.'));return;}
 if(r.revision)markSeen(r);
 const title=el('h2',r.title);title.tabIndex=-1;root.append(title);
 if(r.unconfirmed)root.append(el('p','Ранее проблема была подтверждена. Сейчас данных для проверки её состояния нет.','notice'));
 root.append(el('p',r.detail),table([['Ответственный',r.owner||'Не подтверждён'],['Время наблюдения',r.observedAt?dateLabel(r.observedAt):'Неизвестно'],...r.evidence]));
 if(r.domain&&domains[r.domain]){const source=el('a','Открыть раздел «'+domains[r.domain]+'»','cockpit-action');source.href='#'+r.domain;root.append(source);}
 root.append(el('p','Просмотр не означает решение. Новая или изменившаяся проблема появляется снова; важная остаётся наверху. История до открытия этой вкладки не восстанавливается.','muted small'));
 if(document.activeElement?.closest('#evidence-content')===null)title.focus({preventScroll:true});
}
export function renderCockpit(snapshot,accounts,resources,now,transportError){
 const view=overview(snapshot,accounts,resources,now,transportError);
 let cleared=false;
 for(const r of [...view.records,...active.values()])if(r.state==='clear'||view.retired.includes(r.entity))cleared=seen.delete(opaque(r.id))||cleared;
 if(cleared)saveSeen();
 active=reconcile(active,view.records,view.retired);
 registry=new Map(view.records.map(r=>[opaque(r.id),r]));for(const r of active.values())registry.set(opaque(r.id),r);
 const seenForRows=new Map([...active.values()].map(r=>[r.id,seen.get(opaque(r.id))]));
 const ordered=[...active.values()].sort((a,b)=>Number(b.tone==='critical')-Number(a.tone==='critical')||Number(b.unconfirmed)-Number(a.unconfirmed));
 const expanded=ordered.filter(r=>!compact(r,seenForRows)),viewed=ordered.filter(r=>compact(r,seenForRows));
 const gaps=view.records.filter(r=>r.state==='unknown'&&!active.has(r.id));
 $('cockpit-coverage').replaceChildren(el('strong',`${active.size} нерешённых · ${gaps.length} пробелов`),el('p',view.coverageFresh?'Обновление сводки: 15 мин · актуальность каждого источника — в доказательствах.':'Нет свежего чтения Court / Hermes. Активная работа не подтверждена.','small'));
 $('cockpit-count').textContent=expanded.length+' записей';
 $('cockpit-decisions').replaceChildren(...expanded.map(r=>row(r,now)));
 if(!expanded.length)$('cockpit-decisions').append(el('p',active.size?'Остальное просмотрено и остаётся нерешённым ниже.':'Подтверждённых нерешённых проблем в доступных данных нет. Это не подтверждение полного охвата.','cockpit-empty'));
 $('cockpit-seen').hidden=!viewed.length;$('cockpit-seen-count').textContent='Просмотрено · не решено: '+viewed.length;
 $('cockpit-seen-list').replaceChildren(...viewed.map(r=>row(r,now,{small:true})));
 $('cockpit-unknown-count').textContent='Пробелы в данных: '+gaps.length;$('cockpit-unknown').hidden=!gaps.length;
 $('cockpit-unknown-list').replaceChildren(...gaps.map(r=>row({...r,tone:'unknown',detail:'Нет свежего подтверждения. Откройте источник и время замера.'},now)));
 const events=view.events.map(e=>{
  const record={id:e.id,title:e.title,domain:null,observedAt:e.observedAt,tone:'unknown',badge:e.kind,when:e.dateOnly?e.at:dateLabel(e.at),detail:e.source,evidence:[['Вид даты',e.kind],['Дата',e.dateOnly?e.at+' · время не указано':dateLabel(e.at)],['Источник',e.source]],next:'Посмотреть дату'};
  registry.set(opaque(record.id),record);return row(record,now);
 });
 $('cockpit-events').replaceChildren(...events.slice(0,3));
 if(!events.length)$('cockpit-events').append(el('p','Подтверждённых дат из доступных источников на 7 дней нет. Это не означает отсутствие сроков.','cockpit-empty'));
 if(events.length>3){const more=el('details',null,'cockpit-fold');more.append(el('summary','Ещё дат: '+(events.length-3)),...events.slice(3));$('cockpit-events').append(more);}
 const taskRecords=view.tasks.map(t=>taskRecord(t,now));for(const r of taskRecords)registry.set(opaque(r.id),r);
 $('cockpit-active').replaceChildren(...view.activeTasks.map(t=>row(taskRecord(t,now),now,{scope:'active'})));
 if(!view.activeTasks.length)$('cockpit-active').append(el('p','Подтверждённых активных исполнений нет. Это не доказательство простоя: журнал может быть неполным.','cockpit-empty'));
 $('hermes-tasks').replaceChildren(...taskRecords.map(r=>row(r,now,{scope:'tasks'})));
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

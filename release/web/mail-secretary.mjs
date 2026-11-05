import {relativeTime,dateLabel} from './account-view.mjs';
const evidenceCache=new Map();
const historyCache=new Map();
const el=(tag,text,cls)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;};
const queues={reply_needed:'Я должен ответить',waiting_reply:'Ждём ответа',other:'Другие дела',snoozed:'Отложено',done:'Завершено'};
const kinds={reply:'Ответ по вопросу',renewal:'Продление',payment_notice:'Уведомление об оплате',invoice:'Счёт',reply_needed:'Нужен ответ',access:'Доступ',waiting_reply:'Ожидание ответа',resolved_notice:'Разбор уведомления'};
const services={unknown:'Почтовое дело',excalidraw:'Excalidraw',neon:'Neon',github:'GitHub',google:'Google',yandex:'Яндекс',hostkey:'Hostkey',openai:'OpenAI',anthropic:'Anthropic'};
const blockers={owner_decision:'Нужно решение владельца',current_state_unverified:'Текущее состояние сервиса не подтверждено',awaiting_reply:'Есть уведомление об ожидаемом ответе',technical_review:'Передано в очередь ops; запуск специалиста ещё не подтверждён',notice_reviewed:'Разбор уведомления завершён; состояние сервиса не проверялось'};
const nextActions={review_renewal:'Следующий шаг: решить, нужно ли продление сервиса. Оплата или отмена требуют вашего поручения.',review_invoice:'Следующий шаг: проверить основание счёта и факт оплаты в сервисе; письмо само по себе не доказывает долг.',review_reply:'Следующий шаг: определить, нужен ли ответ и какие сведения можно сообщить. Отправка требует вашего поручения.',review_access:'Следующий шаг: проверить уведомление о доступе через ops; вход или изменение аккаунта требуют отдельного решения.'};
const operations={handoff_queued:'Поставлено в очередь ops',read_pdf:'Прочитана выбранная страница PDF',search:'Поиск новых писем',targeted_search:'Точечный поиск по отправителю',read:'Прочитано выбранное письмо',verify:'Проверена опора на источник',case_recorded:'Сохранено дело',irrelevant_verified:'Проверено отсутствие дела',skill_read:'Прочитан рабочий навык',tool_error:'Операция не завершилась'};
export function secretaryView(data,now,transportError=false){
 const age=now-Date.parse(data?.checked_at);
 const fresh=!!data&&!transportError&&Number.isFinite(age)&&age>=-60000&&age<26*3600e3;
 // Mail publication contains no native process identity or liveness evidence.
 const counts=data?{...data.case_counts,running:0}:null;
 return {fresh,running:false,counts,notice:!data?'Проверка ещё не опубликована. Количество дел неизвестно.':!fresh?'Проверка устарела или недоступна. Сохранённые дела остаются ниже.':data.run_state==='running'?'Текущая работа не подтверждена. Последний запуск мог прерваться.':data.stop_reason==='batch_complete'?'Ограниченный пакет разобран. Полнота почтового архива не проверялась.':data.stop_reason==='source_unavailable'?'Часть источников недоступна. Очередь сохранена.':data.stop_reason==='model_unavailable'?'Разбор остановился: ответ агента не подтверждён. Очередь сохранена.':'Пакет завершён. Оставшиеся письма сохранены в очереди.'};
}
export function renderSecretary(data,now,transportError=false,control=null){
 let section=document.getElementById('mail-secretary');
 if(!section){section=el('aside',undefined,'mail-secretary');section.id='mail-secretary';section.setAttribute('aria-label','Почтовый секретарь');document.getElementById('cockpit-coverage').after(section);}
 if(section.contains(document.activeElement)&&document.activeElement.tagName==='INPUT')return;
 const open=new Set([...section.querySelectorAll('details[open]')].map(d=>d.dataset.case));
 const view=secretaryView(data,now,transportError);
 const decisions=control?.available?control.decisions:{};
 const rows=(data?.cases||[]).map(r=>({...r,state:effectiveState(r,decisions[r.id])}));
 const queueCounts=control?.available&&control.queue_counts?control.queue_counts:Object.fromEntries(Object.keys(queues).map(key=>[key,data&&!data.omitted_cases?rows.filter(r=>caseQueue(r,decisions[r.id])===key).length:null]));
 if(view.counts){if(control?.case_counts)Object.assign(view.counts,control.case_counts);else for(let i=0;i<rows.length;i++){const old=data.cases[i].state;if(old!==rows[i].state){view.counts[old]--;view.counts[rows[i].state]++;}}}
 const title=el('h2');const icon=el('img');icon.src='/assets/mail-envelope.png';icon.alt='';icon.width=18;icon.height=18;title.append(icon,document.createTextNode('Почтовый секретарь'));
 section.replaceChildren(title,el('p',view.notice,'muted small'));
 if(data){const brief=el('div',undefined,'mail-brief');brief.append(el('strong','Ежедневная сводка'),briefCounts(view.counts.needs_user,data.pending,queueCounts),el('small','Проверено '+dateLabel(data.checked_at)));section.append(brief);}
 section.append(el('p','Автоматическая проверка — при ежедневном запуске. Подтверждения процессов — в разделе Hermes.','muted small'));
 if(!control?.available)section.append(el('p','Действия временно недоступны. Сохранённые решения не изменены.','muted small'));

 for(const [queue,label] of Object.entries(queues)){
  const group=el('section',undefined,'mail-state mail-'+queue);const heading=el('h3',label);heading.append(el('span',queueCounts[queue]===null?'—':String(queueCounts[queue]),'mail-count'));group.append(heading);
  for(const row of rows.filter(r=>(control?.available&&control.queues?.[r.id]||caseQueue(r,decisions[r.id]))===queue)){
   const d=el('details');d.dataset.case=row.id;d.open=open.has(row.id);
   d.append(el('summary',`${services[row.service]} · ${kinds[row.kind]}`));
   const decision=decisions[row.id];
   const handoff=control?.handoffs?.[row.id];
   if(handoff)d.append(el('p',handoffLabel(handoff),'mail-handoff small'));
   if(decision)d.append(el('p',decisionLabel(decision),'mail-decision small'));
   if((!decision||['checked','due','cancelled'].includes(decision.status))&&!(handoff&&row.next_action==='ops_review'))d.append(el('p',nextActions[row.next_action]|| (row.next_action==='review_notice'?'Следующий шаг: рассмотреть уведомление и решить, нужен ли ответ или действие.':row.next_action==='ops_review'?'Следующий шаг: техническая проверка через ops.':row.next_action==='check_latest'?'Следующий шаг: проверить более свежие сведения.':'Следующий шаг не требуется для разбора этого уведомления.'),'small'));
   d.append(el('p',row.deadline?'Срок из письма: '+row.deadline:'Срок неизвестен','small'));
   if((!decision||decision.status==='checked')&&!handoff)d.append(el('p',blockers[row.blocker],'small'));
   d.append(el('p','Уверенность: подтверждено содержание уведомления, не текущее состояние сервиса.','muted small'));
   d.append(el('p','Ответственный: '+({user:'Вы',ops:'Hermes · ops','mail-secretary':'Почтовый секретарь'}[row.owner]),'muted small'));
   const latestHandoff=handoff&&Date.parse(handoff.at)>=Date.parse(row.updated_at)?handoff:null;
   const lastOperation=latestHandoff?(latestHandoff.diagnostic_completed?'выполнена ограниченная диагностика infra-dev':latestHandoff.status==='queued'?'поставлено в очередь ops':latestHandoff.status==='dispatching'?'запрошен запуск infra-dev':'результат infra-dev не подтверждён'):(row.last_operation==='handoff_queued'?'поставлено в очередь ops':'проверена опора на источник');
   d.append(el('p','Последняя операция: '+lastOperation+' · '+relativeTime(latestHandoff?.at||row.updated_at,now),'muted small'));
   d.append(el('p','Источник от '+dateLabel(row.observed_at)+' · '+row.sources.map(s=>s.slice(0,8)).join(', '),'muted small'));
   d.append(caseControls(row,decision,!!control?.available,open));
   group.append(d);
  }
  section.append(group);
 }
 if(data){
  if(data.omitted_cases)section.append(el('p',`Показано ${data.cases.length} из ${data.cases.length+data.omitted_cases} дел. Остальные сохранены; счётчики учитывают все дела.`,'muted small'));
  const detail=el('details');detail.dataset.case='operations';detail.open=open.has('operations');detail.append(el('summary','Подробнее · действия и охват'));
  detail.append(el('p',`В очереди: ${data.pending}. Доступны: ${data.coverage.ok}; неполный охват: ${data.coverage.partial}; недоступны: ${data.coverage.unavailable}.`,'small'));
  for(const operation of data.operations.slice(-8))detail.append(el('p',(operations[operation.action]||'Операция')+' · '+(operation.outcome==='ok'?'выполнено':'не подтверждено')+' · '+relativeTime(operation.at,now),'muted small'));
  detail.append(el('p','Ограниченная проверка входящих, исходящих Gmail и открытых переписок. Ответ снимает напоминание после проверки связи с вопросом. Архивный разбор остановлен. Письма не отправляются и не изменяются.','muted small'));section.append(detail);
 }
}

export function effectiveState(row,decision){
 const status=decision?.status;
 return status==='resolved'?'done':status==='due'?'needs_user':['snoozed','queued','running','blocked'].includes(status)?'waiting':row.state;
}
export function caseQueue(row,decision){
 if(effectiveState(row,decision)==='done')return 'done';
 if(decision?.status==='snoozed')return 'snoozed';
 return ['reply_needed','waiting_reply'].includes(row.kind)?row.kind:'other';
}
export function handoffLabel(h){
 if(h.status==='queued')return 'Техническая проверка: заявка сохранена для ops.';
 if(h.status==='dispatching')return 'Ops запросил запуск infra-dev. Результат ещё не получен.';
 if(h.reason==='diagnostic_scope_limited'&&h.diagnostic_completed)return 'infra-dev проверил локальный почтовый канал. Доступ к внешнему сервису этой проверкой не проверялся. Состояние дела не изменено.';
 if(h.reason==='diagnostic_unavailable'&&h.diagnostic_completed)return 'infra-dev выполнил диагностику: локальный почтовый канал доступен не полностью. Нужна проверка ops.';
 return 'Исполнение infra-dev не подтверждено. Повторный запуск автоматически не создан; можно снова выбрать «Разобраться».';
}
export function decisionLabel(d){
 if(d.status==='cancelled')return 'Напоминание отменено: '+(d.reason==='question_resolved'?'вопрос решён по проверенному письму.':'получен ответ по этому вопросу.');
 return ({resolved:'Вы отметили дело решённым. Решение сохранено.',snoozed:'Напомнить '+d.remind_on+' по Стамбулу. До этой даты дело отложено.',due:'Наступила выбранная дата напоминания: '+d.remind_on,queued:'Разобраться: в очереди ближайшего ежедневного запуска.',running:'Запрос принят в текущий разбор.',checked:'Повторная проверка источника завершена. Результат — в карточке.',blocked:'Разбор начат, но подтверждённого результата пока нет. Запрос сохранён.'})[d.status]||'Решение сохранено.';
}
async function mailPost(path,value){
 const response=await fetch('/api/mail-secretary/'+path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(value)});
 const result=await response.json();
 if(!response.ok)throw new Error(path!=='action'?'Сведения сейчас недоступны. Сохранённые данные не изменены.':result.error==='invalid_reminder'?'Выберите будущую дату не дальше одного года.':response.status===409?'Решение изменилось в другой вкладке. Обновите страницу.':response.status===401?'Войдите снова. Решение не отправлено.':'Не удалось подтвердить сохранение. Повторите попытку.');
 return result;
}
function caseControls(row,decision,available,open){
 const box=el('div',undefined,'mail-controls');const status=el('p','','small');status.setAttribute('role','status');status.setAttribute('aria-live','polite');
 const evidence=el('div',undefined,'mail-evidence');const show=el('button','Показать доказательства');show.type='button';show.disabled=!available;
 const displayProof=proof=>{evidence.replaceChildren(el('strong','Доказательства'),el('p','Письмо от '+dateLabel(proof.observed_at),'small'),el('p',proof.deadline?'Подтверждённый срок: '+proof.deadline:'Явный срок не найден','small'));
 if(proof.excerpt)evidence.append(el('blockquote',proof.excerpt));
 else evidence.append(el('p',proof.status==='source_changed'?'Источник изменился. Нужна повторная проверка.':'Сохранены сведения об источнике. Для проверенного фрагмента нажмите «Разобраться».','muted small'));
 evidence.append(el('p','Подтверждено содержание уведомления, не текущее состояние сервиса.','muted small'));};
 show.onclick=async()=>{show.disabled=true;try{const proof=await mailPost('evidence',{case_id:row.id});evidenceCache.set(row.id,{proof,at:Date.now(),version:row.updated_at});displayProof(proof);}catch(error){status.textContent=error.message;show.disabled=false;}};
 const cached=evidenceCache.get(row.id);
 if(cached&&cached.version===row.updated_at&&Date.now()-cached.at<300000)displayProof(cached.proof);
 else {evidenceCache.delete(row.id);evidence.append(show);}
 box.append(evidence);
 box.append(caseHistory(row,decision,available,open));
 const actions=el('div',undefined,'mail-actions');const investigate=el('button','Разобраться','mail-primary');const remind=el('button','Напомнить');const resolved=el('button','Уже решено');
 for(const b of [investigate,remind,resolved]){b.type='button';b.disabled=!available;}
 const picker=el('form',undefined,'mail-reminder');picker.hidden=true;const label=el('label','Дата напоминания (Стамбул)');const date=el('input');date.type='date';date.required=true;label.append(date);const save=el('button','Сохранить дату');save.type='submit';picker.append(label,save);
 const today=new Date().toLocaleDateString('en-CA',{timeZone:'Europe/Istanbul'});const tomorrow=new Date(today+'T12:00:00Z');tomorrow.setUTCDate(tomorrow.getUTCDate()+1);date.min=tomorrow.toISOString().slice(0,10);date.value=date.min;
 let pending=null;
 const send=async(action,remind_on=null)=>{
  if(!pending||pending.action!==action||pending.remind_on!==remind_on)pending={case_id:row.id,action,remind_on,request_id:crypto.randomUUID().replaceAll('-',''),expected:decision?.request_id||null};
  for(const b of [investigate,remind,resolved,save])b.disabled=true;
  status.textContent='Сохраняем…';
  try{const updated=await mailPost('action',pending);dispatchEvent(new CustomEvent('mail-secretary-change',{detail:updated}));}
  catch(error){status.textContent=error.message;for(const b of [investigate,remind,resolved,save])b.disabled=!available;}
 };
 investigate.onclick=()=>send('investigate');resolved.onclick=()=>send('resolved');remind.onclick=()=>{picker.hidden=!picker.hidden;if(!picker.hidden)date.focus();};
 picker.onsubmit=e=>{e.preventDefault();date.blur();send('remind',date.value);};
 actions.append(investigate,remind,resolved);box.append(actions,picker,status);return box;
}

function briefCounts(decisions,pending,counts){const grid=el('div',undefined,'mail-brief-counts');for(const [count,label] of [[counts.reply_needed,'я должен ответить'],[counts.waiting_reply,'ждём ответа'],[decisions,'к решению'],[pending,'писем в очереди']]){const item=el('div');item.append(el('b',count===null?'—':String(count)),el('span',label));grid.append(item);}return grid;}

export function historyLabel(event){
 if(event.event==='reminder_cancelled')return 'Напоминание отменено: '+({reply_received:'получен ответ',question_resolved:'вопрос решён по письму',owner_resolved:'вы отметили вопрос решённым'}[event.reason]||'причина неизвестна');
 return ({source_verified:'Проверен источник',incoming_request:'Получен запрос — нужен ваш ответ',sent_request:'Отправленный запрос — ждём ответа',reply_received:'Проверен новый ответ по вопросу',reply_sent:'Проверен ваш отправленный ответ',question_resolved:'Письмо подтверждает решение вопроса',owner_investigate:'Вы выбрали «Разобраться»',owner_resolved:'Вы отметили «Уже решено»',owner_remind:'Вы назначили напоминание на '+event.remind_on})[event.event]||'Событие дела';
}
function caseHistory(row,decision,available,open){
 const detail=el('details',undefined,'mail-history');detail.dataset.case=row.id+':history';detail.open=open.has(detail.dataset.case);detail.append(el('summary','История дела'));
 const body=el('div');const load=el('button','Показать историю');load.type='button';load.disabled=!available;
 const version=row.updated_at+':'+(decision?.request_id||'');
 const display=value=>{body.replaceChildren();const list=el('ol',undefined,'mail-timeline');
  for(const event of value.events){const item=el('li');const time=el('time',dateLabel(event.at),'muted small');time.dateTime=event.at;item.append(time,el('p',historyLabel(event),'small'));if(event.ref)item.append(el('small','Источник '+event.ref.slice(0,8)));list.append(item);}
  body.append(list);if(value.omitted)body.append(el('p','Показаны последние 50 событий. Более ранних сохранено: '+value.omitted,'muted small'));
  if(value.legacy)body.append(el('p','Ранние изменения до v3 не записывались. Показаны сохранённый источник и ваши решения.','muted small'));
 };
 const cached=historyCache.get(row.id);if(cached&&cached.version===version&&Date.now()-cached.at<300000)display(cached.value);else body.append(load);
 load.onclick=async()=>{load.disabled=true;try{const value=await mailPost('history',{case_id:row.id});historyCache.set(row.id,{value,version,at:Date.now()});display(value);}catch(error){load.disabled=false;let status=body.querySelector('[role=status]');if(!status){status=el('p','','small');status.setAttribute('role','status');body.append(status);}status.textContent=error.message;}};
 detail.append(body);return detail;
}

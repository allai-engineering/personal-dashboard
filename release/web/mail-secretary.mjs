import {relativeTime,dateLabel} from './account-view.mjs';
const el=(tag,text,cls)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;};
const states={needs_user:'Нужно ваше решение',running:'Hermes занимается',waiting:'Ждём ответа',done:'Завершено'};
const kinds={renewal:'Продление',payment_notice:'Уведомление об оплате',invoice:'Счёт',reply_needed:'Нужен ответ',access:'Доступ',waiting_reply:'Ожидание ответа',resolved_notice:'Разбор уведомления'};
const services={unknown:'Почтовое дело',excalidraw:'Excalidraw',neon:'Neon',github:'GitHub',google:'Google',yandex:'Яндекс',hostkey:'Hostkey',openai:'OpenAI',anthropic:'Anthropic'};
const blockers={owner_decision:'Нужно решение владельца',current_state_unverified:'Текущее состояние сервиса не подтверждено',awaiting_reply:'Есть уведомление об ожидаемом ответе',technical_review:'Передано в очередь ops; запуск специалиста ещё не подтверждён',notice_reviewed:'Разбор уведомления завершён; состояние сервиса не проверялось'};
const operations={handoff_queued:'Поставлено в очередь ops',read_pdf:'Прочитана выбранная страница PDF',search:'Поиск новых писем',targeted_search:'Точечный поиск по отправителю',read:'Прочитано выбранное письмо',verify:'Проверена опора на источник',case_recorded:'Сохранено дело',irrelevant_verified:'Проверено отсутствие дела',skill_read:'Прочитан рабочий навык',tool_error:'Операция не завершилась'};
export function secretaryView(data,now,transportError=false){
 const age=now-Date.parse(data?.checked_at);
 const fresh=!!data&&!transportError&&Number.isFinite(age)&&age>=-60000&&age<26*3600e3;
 const running=fresh&&data.run_state==='running'&&age<10*60e3;
 const counts=data?Object.fromEntries(Object.keys(states).map(s=>[s,s==='running'?(running?1:0):data.cases.filter(r=>r.state===s).length])):null;
 return {fresh,running,counts,notice:!data?'Проверка ещё не опубликована. Количество дел неизвестно.':!fresh?'Проверка устарела или недоступна. Сохранённые дела остаются ниже.':running?'Идёт ограниченный разбор почты.':data.run_state==='running'?'Текущая работа не подтверждена. Последний запуск мог прерваться.':data.stop_reason==='batch_complete'?'Ограниченный пакет разобран. Полнота почтового архива не проверялась.':data.stop_reason==='source_unavailable'?'Часть источников недоступна. Очередь сохранена.':data.stop_reason==='model_unavailable'?'Разбор остановился: ответ агента не подтверждён. Очередь сохранена.':'Пакет завершён. Оставшиеся письма сохранены в очереди.'};
}
export function renderSecretary(data,now,transportError=false){
 let section=document.getElementById('mail-secretary');
 if(!section){section=el('aside',undefined,'mail-secretary');section.id='mail-secretary';section.setAttribute('aria-label','Почтовый секретарь');document.getElementById('page-overview').append(section);}
 const open=new Set([...section.querySelectorAll('details[open]')].map(d=>d.dataset.case));
 const view=secretaryView(data,now,transportError);
 const title=el('h2');const icon=el('img');icon.src='/assets/mail-envelope.svg';icon.alt='';icon.width=18;icon.height=18;title.append(icon,document.createTextNode('Почтовый секретарь'));
 section.replaceChildren(title,el('p',view.notice,'muted small'));
 for(const [state,label] of Object.entries(states)){
  const group=el('section',undefined,'mail-state mail-'+state);const heading=el('h3',label);heading.append(el('span',view.counts?String(view.counts[state]):'—','mail-count'));group.append(heading);
  if(state==='running')group.append(el('p',view.running?'Активен текущий запуск':'Активная работа не подтверждена','muted small'));
  for(const row of (data?.cases||[]).filter(r=>r.state===state)){
   const d=el('details');d.dataset.case=row.id;d.open=open.has(row.id);
   d.append(el('summary',`${services[row.service]} · ${kinds[row.kind]}`));
   d.append(el('p',row.next_action==='review_notice'?'Следующий шаг: рассмотреть уведомление и решить, нужен ли ответ или действие.':row.next_action==='ops_review'?'Следующий шаг: техническая проверка через ops.':row.next_action==='check_latest'?'Следующий шаг: проверить более свежие сведения.':'Следующий шаг не требуется для разбора этого уведомления.','small'));
   d.append(el('p',row.deadline?'Срок из письма: '+row.deadline:'Срок неизвестен','small'));
   d.append(el('p',blockers[row.blocker],'small'));
   d.append(el('p','Уверенность: подтверждено содержание уведомления, не текущее состояние сервиса.','muted small'));
   d.append(el('p','Ответственный: '+({user:'Вы',ops:'Hermes · ops','mail-secretary':'Почтовый секретарь'}[row.owner]),'muted small'));
   d.append(el('p','Последняя операция: проверена опора на источник · '+relativeTime(row.updated_at,now),'muted small'));
   d.append(el('p','Источник от '+dateLabel(row.observed_at)+' · '+row.sources.map(s=>s.slice(0,8)).join(', '),'muted small'));
   group.append(d);
  }
  section.append(group);
 }
 if(data){
  const detail=el('details');detail.dataset.case='operations';detail.open=open.has('operations');detail.append(el('summary','Подробнее · действия и охват'));
  detail.append(el('p',`В очереди: ${data.pending}. Доступны: ${data.coverage.ok}; неполный охват: ${data.coverage.partial}; недоступны: ${data.coverage.unavailable}.`,'small'));
  for(const operation of data.operations.slice(-8))detail.append(el('p',(operations[operation.action]||'Операция')+' · '+(operation.outcome==='ok'?'выполнено':'не подтверждено')+' · '+relativeTime(operation.at,now),'muted small'));
  detail.append(el('p','Входящие за ограниченный период и точечный поиск. Архивный разбор остановлен. Письма не отправляются и не изменяются.','muted small'));section.append(detail);
 }
}

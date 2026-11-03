import {integrationRows} from './integrations-view.mjs';
import {sortedBalances,sortedMachines,freshAt} from './operations-view.mjs';
import {relativeTime,dateLabel} from './account-view.mjs';
const $=id=>document.getElementById(id), el=(tag,text,cls)=>{const n=document.createElement(tag);if(text!=null)n.textContent=text;if(cls)n.className=cls;return n;};
const amount=(n,unit)=>new Intl.NumberFormat('ru-RU',{maximumFractionDigits:unit==='credits'?0:2}).format(n)+(unit==='credits'?' кр.':' $');
const kinds={physical:'Сервер',physical_mac:'Mac',cloud_vm:'Облачная VM',virtual_machine:'VM',wsl_guest:'WSL',managed_kubernetes_node:'Узел Kubernetes',physical_router:'Роутер',services:'Приложения и бэкапы',unknown:'Тип не подтверждён'};
const pages={overview:'Мостик',courts:'Суды',subscriptions:'Подписки',balances:'Балансы',machines:'Машины',hermes:'Hermes',evidence:'Доказательства'};
let latest=null;
export function initNavigation(){
 function show(){
  const route=location.hash.slice(1).split('/')[0],page=Object.hasOwn(pages,route)?route:'overview';
  for(const [id,title] of Object.entries(pages)){
   $('page-'+id).hidden=page!==id;
   const link=$('nav-'+id);if(!link)continue;link.classList.toggle('active',page===id);if(page===id)link.setAttribute('aria-current','page');else link.removeAttribute('aria-current');
  }
  $('page-title').textContent=pages[page];
  if(latest)observation(...latest);
 }
 addEventListener('hashchange',show);show();
}
export function observationView(snapshot,transportError,now,hash){
 const page=hash.slice(1).split('/')[0];
 const value=page==='subscriptions'?snapshot?.observed_at_utc:['balances','machines'].includes(page)?snapshot?.operations?.collected_at:snapshot?.cockpit?.collected_at;
 return {text:transportError?'Не удалось обновить данные':value?`Снимок ${relativeTime(value,now)}`:snapshot?'Время обновления неизвестно':'Получаем данные…',title:value?dateLabel(value):''};
}
function observation(snapshot,transportError,now){const view=observationView(snapshot,transportError,now,location.hash);$('observation').textContent=view.text;$('observation').title=view.title;}
function badge(tone){return el('span',{critical:'Важно',warning:'Внимание',unknown:'Нет данных',ok:'Замер получен'}[tone],'badge '+tone);}
function detail(root,label,value){const p=el('p',null,'small');p.append(el('span',label+': ','muted'),document.createTextNode(value));root.append(p);}
function disclosure(card,key,open){const d=el('details');d.dataset.operation=key;d.open=open.has(key);d.append(el('summary','Подробнее'));card.append(d);return d;}
export function machineAction(m){
 if(!m.hostFresh)return 'Получить свежий замер диагностики.';
 if(m.state==='not_enrolled')return 'Подключить диагностику через подтверждённый доступ.';
 if(m.state==='unreachable')return 'Проверить машину и восстановить канал диагностики.';
 const codes=new Set(m.active.filter(i=>i.severity!=='unknown').map(i=>i.code));
 if(codes.has('disk'))return 'Проверить, чем занят диск, и выбрать, что можно убрать.';
 if(codes.has('backup'))return 'Проверить результат последней резервной копии.';
 if(codes.has('service')||codes.has('application'))return 'Открыть проверку службы или приложения в «Подробнее».';
 return ['critical','warning'].includes(m.tone)?'Открыть подробности проверки Hermes.':null;
}
function balanceCard(b,now,open){
 const card=el('article',null,'account resource-card '+b.tone);card.id='balance-'+b.id;
 const head=el('div',null,'service-top');head.append(el('h2',b.title),badge(b.tone));card.append(head);
 const label=b.amount===null?'Остаток неизвестен':b.billed?'Начислено за период':b.noPrepayment?'Предоплаты нет':b.id==='digitalocean'?'Предоплата после начислений':'Осталось';
 card.append(el('p',label,'muted small'));
 card.append(el('p',b.amount===null?'Нет данных':b.noPrepayment&&!b.billed?'—':amount(b.amount,b.unit),'balance-value'+(b.amount===null?' unknown':'')));
 if(b.problem)card.append(el('p',b.problem,'small'));
 if(b.month_spend!==null&&b.amount!==null)card.append(el('p',`Расход за месяц: ${amount(b.month_spend,'USD')}`,'small'));
 card.append(el('p',`Данные ${relativeTime(b.source_at,now)}`,'muted small'));
 const d=disclosure(card,'balance-'+b.id,open);
 detail(d,'Последняя проверка',dateLabel(b.observed_at));detail(d,'Срез сервиса',dateLabel(b.source_at));
 detail(d,'Источник',b.id==='digitalocean'?'DigitalOcean Billing API':b.title+' Credits API');
 if(b.id==='digitalocean')d.append(el('p','Предоплата показана с учётом начислений текущего месяца. Начисления не означают просрочку. Срез биллинга может отставать от времени проверки.','muted small'));
 else d.append(el('p',b.unit==='credits'?'Кредиты Kie, не доллары. Предупреждение ниже 5 000 кр.; красный ниже 2 000 кр.':'Остаток аккаунта OpenRouter, не лимит отдельного ключа. Предупреждение ниже $25; красный ниже $10.','muted small'));
 return card;
}
function machineCard(m,now,open){
 const card=el('article',null,'account resource-card '+m.tone);card.id='machine-'+m.id;
 const head=el('div',null,'service-top');head.append(el('h2',m.id==='applications'?'Приложения и бэкапы':m.id),badge(m.tone));card.append(head);
 if(m.aliases?.length)card.append(el('p','Псевдонимы: '+m.aliases.join(', '),'muted small'));
 card.append(el('p',m.message,'resource-message'));
 const action=machineAction(m);if(action)card.append(el('p','Что сделать: '+action,'small'));
 const when=m.active.find(i=>i.severity!=='unknown')?.observed_at||m.observed_at;
 card.append(el('p',`Замер ${relativeTime(when,now)}`,'muted small'));
 const d=disclosure(card,'machine-'+m.id,open);detail(d,'Тип',kinds[m.kind]);detail(d,'Проверка машины',dateLabel(m.observed_at));
 if(!m.hostFresh)d.append(el('p','Измерения ниже исторические; текущее состояние неизвестно.','warning small'));
 const metrics=m.metrics, n=(v,suffix)=>typeof v==='number'?new Intl.NumberFormat('ru-RU',{maximumFractionDigits:1}).format(v)+suffix:'Не измерено';
 detail(d,'Минимум свободного диска',n(metrics.disk_free_percent,'%'));
 detail(d,'Доступная память',n(metrics.memory_available_percent,'%'));
 detail(d,'Нагрузка за 1 мин / CPU',n(metrics.load1,'')+' / '+n(metrics.cpu_count,''));
 for(const i of m.issues){const active=m.active.includes(i);d.append(el('p',i.text+' · '+relativeTime(i.observed_at,now)+(active?'':' · устарело / не подтверждено'),'small '+(active&&i.severity!=='unknown'?'warning':'muted')));}
 d.append(el('p','Источник — Hermes. Доступность машины не доказывает работу приложения. Список включает VM, устройства и неподтверждённые записи.','muted small'));
 return card;
}
function integrationCard(r,now,open){
 const card=el('article',null,'account resource-card '+r.tone);
 const head=el('div',null,'service-top');head.append(el('h2',r.title),badge(r.tone));card.append(head);
 if(r.plan)card.append(el('p',r.plan,'muted small'));
 if(r.kind==='balance')card.append(el('p',r.value===null?'Остаток неизвестен':new Intl.NumberFormat('ru-RU',{maximumFractionDigits:2}).format(r.value)+' '+(r.unit||''),'balance-value'));
 if(r.kind==='account')for(const [key,label,reset] of [['weekly_remaining','Неделя','weekly_reset_at'],['five_hour_remaining','5 часов','five_hour_reset_at']]){
  card.append(el('p',label+': '+(r[key]===null?'неизвестно':Math.round(r[key])+'%')+(r[key]!==null&&r[reset]?' · сброс '+relativeTime(r[reset],now):''),'small'));
 }
 if(r.problem)card.append(el('p',r.problem,'small'));
 card.append(el('p',`Данные ${relativeTime(r.observed_at,now)}`,'muted small'));
 const d=disclosure(card,'integration-'+r.key,open);detail(d,'Источник',r.source);detail(d,'Замер',dateLabel(r.observed_at));return card;
}
export function renderOperations(snapshot,transportError,now){
 latest=[snapshot,transportError,now];observation(...latest);
 const ops=snapshot?.operations,balances=sortedBalances(ops,now,transportError),machines=sortedMachines(ops,now,transportError);
 const open=new Set([...document.querySelectorAll('details[data-operation][open]')].map(n=>n.dataset.operation));
 const balancesRoot=$('balances');balancesRoot.replaceChildren(...balances.map(b=>balanceCard(b,now,open)));
 const machineRoot=$('machines');machineRoot.replaceChildren(...machines.map(m=>machineCard(m,now,open)));
 const okay=!transportError&&freshAt(ops?.collected_at,now,1800);
 $('operations-notice').hidden=okay;$('operations-notice').textContent='Нет свежего снимка машин и балансов. Числа не считаются текущими.';
 $('source-status').textContent=okay?'Источники и обновление':'Есть пробелы в данных · Подробнее';
 for(const [root,missing,text] of [[balancesRoot,!balances.length,'Данные балансов пока недоступны.'],[machineRoot,!machines.length,'Реестр Hermes недоступен. Это не означает отсутствие машин.']])if(missing){
  const state=el('div',null,'empty-state');state.append(el('h2',text),el('p',ops?.collected_at?'Снимок источника: '+dateLabel(ops.collected_at):'Время снимка источника неизвестно.','muted small'),el('p','Сбор данных работает по расписанию. Кнопка «Обновить» перечитывает сохранённый снимок.','muted small'));root.append(state);
 }
 const count=ops?.fleet?.inventory_count,enrolled=ops?.fleet?.enrolled;
 $('machine-count').textContent=typeof count==='number'?`${count} записей в реестре · диагностика подключена: ${enrolled} · без свежего состояния: ${machines.filter(m=>m.tone==='unknown').length}`:'Охват машин неизвестен';
 const integrated=integrationRows(snapshot?.integrations,now,transportError);
 for(const page of ['subscriptions','balances','machines']){
  let root=$('integrations-'+page);
  if(!root){root=el('div',null,'accounts');root.id='integrations-'+page;$('page-'+page).append(root);}
  root.replaceChildren(...integrated.filter(r=>r.page===page).map(r=>integrationCard(r,now,open)));
 }
 return {balances,machines,integrated};
}

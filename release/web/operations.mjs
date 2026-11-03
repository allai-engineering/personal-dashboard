import {incidentView,maintenanceWork,preparationLabel} from './cockpit-view.mjs';
import {integrationRows} from './integrations-view.mjs';
import {sortedBalances,sortedMachines,freshAt,machineCondition} from './operations-view.mjs';
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
export function batteryView(m,now,transportError=false){
 const b=m.battery,fresh=!transportError&&b?.status==='ok'&&freshAt(b.observed_at,now,1800)&&freshAt(b.checked_at,now,1800);
 const n=v=>Number.isInteger(v)&&v>=0&&v<=100?v:null;
 if(!fresh)return {fresh:false,tone:'unknown',label:transportError?'Не удалось обновить батарею · 80% не подтверждены':b?.status==='ok'?'Данные батареи устарели · 80% не подтверждены':'Нет связи с датчиком батареи · 80% не подтверждены',charge:null,health:null,condition:'неизвестно',at:b?.checked_at};
 const limit=b.limit_status==='ok'?n(b.limit_percent):null,confirmed=limit===80&&b.limit_enabled===true;
 return {fresh:true,charge:n(b.charge_percent),health:n(b.health_percent),condition:{normal:'нормальное',service_recommended:'рекомендуется обслуживание',unknown:'неизвестно'}[b.health_condition]||'неизвестно',
  tone:confirmed?'ok':limit!==null?'warning':'unknown',label:confirmed?'Лимит 80% подтверждён':limit===null?'Лимит неизвестен · 80% не подтверждены':b.limit_enabled===false?'Лимит выключен · 80% не подтверждены':`Лимит ${limit}% · требуется 80%`,at:b.observed_at};
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
function machineCard(m,now,open,transportError,work){
 const card=el('article',null,'account resource-card '+m.tone);card.id='machine-'+m.id;
 const head=el('div',null,'service-top');head.append(el('h2',m.id==='applications'?'Приложения и бэкапы':m.id),badge(m.tone));card.append(head);
 if(m.aliases?.length)card.append(el('p','Псевдонимы: '+m.aliases.join(', '),'muted small'));
 const battery=m.kind==='physical_mac'?batteryView(m,now,transportError):null;
 if(battery){
  card.append(el('p',`Заряд: ${battery.charge===null?'неизвестен':battery.charge+'%'} · Здоровье: ${battery.health===null?'неизвестно':battery.health+'%'}`,'small'));
  const limit=el('p',null,'small '+(battery.tone==='unknown'?'muted':battery.tone==='warning'?'warning':''));limit.append(el('strong',battery.label));card.append(limit);
  card.append(el('p',`Батарея: ${battery.fresh?'замер':'проверка'} ${relativeTime(battery.at,now)}`,'muted small'));
 }
 card.append(el('p',m.message,'resource-message'));
 const record={id:'machine-'+m.id,condition_key:machineCondition(m),state:m.tone==='ok'?'clear':['critical','warning'].includes(m.tone)?'open':'unknown'};
 const stage=m.tone==='ok'?maintenanceWork(record,work,now,transportError):incidentView(record,work,now,transportError);
 if(stage){
  card.append(el('p','Hermes: '+stage.label,'small'));
  if(stage.action)card.append(el('p','Последний этап: '+stage.action,'small'));
  if(stage.blocker)card.append(el('p',stage.blocker,'small'));
  if(preparationLabel(stage.item))card.append(el('p',preparationLabel(stage.item)+' · '+relativeTime(stage.item.preparation.tested_at,now),'small'));
  if(stage.lane==='owner')card.append(el('p','Нужно от вас: '+stage.item.decision,'small'));
 }
 const when=m.active.find(i=>i.severity!=='unknown')?.observed_at||m.observed_at;
 card.append(el('p',`Замер ${relativeTime(when,now)}`,'muted small'));
 const d=disclosure(card,'machine-'+m.id,open);detail(d,'Тип',kinds[m.kind]);detail(d,'Проверка машины',dateLabel(m.observed_at));
 if(battery){
  detail(d,'Состояние батареи',battery.condition);detail(d,'Циклы',battery.fresh&&Number.isInteger(m.battery.cycle_count)?String(m.battery.cycle_count):'Неизвестно');
  detail(d,'Замер батареи',dateLabel(m.battery?.observed_at));
  d.append(el('p','Здоровье — максимальная ёмкость по данным macOS. Подтверждённый лимит — прочитанная настройка; macOS иногда заряжает до 100% для калибровки.','muted small'));
 }
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
 const machineRoot=$('machines');machineRoot.replaceChildren(...machines.map(m=>machineCard(m,now,open,transportError,snapshot?.cockpit?.work)));
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

import {integrationRows} from './integrations-view.mjs';
const operationIcons={"27": "/assets/cutout-27-c9bc9c75f9dd.png", "1": "/assets/cutout-1-cafa1f33bb15.png", "21": "/assets/cutout-21-ec68832ade0e.png", "42": "/assets/cutout-42-f0cbed3e8905.png", "51": "/assets/cutout-51-786235fc9dca.png", "34": "/assets/cutout-34-ab09e3bda00e.png", "16": "/assets/cutout-16-c315cbc1b9b9.png"};
import {sortedBalances,sortedMachines,freshAt} from './operations-view.mjs';
import {relativeTime,dateLabel,windowLabel} from './account-view.mjs';
const $=id=>document.getElementById(id), el=(tag,text,cls)=>{const n=document.createElement(tag);if(text!=null)n.textContent=text;if(cls)n.className=cls;return n;};
const amount=(n,unit)=>new Intl.NumberFormat('ru-RU',{maximumFractionDigits:unit==='credits'?0:2}).format(n)+(unit==='credits'?' кр.':' $');
const kinds={physical:'Сервер',physical_mac:'Mac',cloud_vm:'Облачная VM',virtual_machine:'VM',wsl_guest:'WSL',managed_kubernetes_node:'Узел Kubernetes',physical_router:'Роутер',services:'Приложения и бэкапы',unknown:'Тип не подтверждён'};
const pages={overview:'Обзор',subscriptions:'Подписки',balances:'Балансы',machines:'Машины'};
let latest=null;
export function initNavigation(){
 function show(){
  const page=Object.hasOwn(pages,location.hash.slice(1))?location.hash.slice(1):'overview';
  for(const [id,title] of Object.entries(pages)){
   $('page-'+id).hidden=page!==id;
   const link=$('nav-'+id);link.classList.toggle('active',page===id);if(page===id)link.setAttribute('aria-current','page');else link.removeAttribute('aria-current');
  }
  $('page-title').textContent=pages[page];
  if(latest)observation(...latest);
 }
 addEventListener('hashchange',show);show();
}
function observation(snapshot,transportError,now){
 const value=location.hash==='#subscriptions'?snapshot?.observed_at_utc:snapshot?.operations?.collected_at;
 $('observation').textContent=transportError?'Не удалось обновить данные':value?`Получено ${relativeTime(value,now)} · давность замеров указана отдельно`:'Получаем данные…';
 $('observation').title=value?dateLabel(value):'';
}
function icon(id){const img=document.createElement('img');img.src=operationIcons[id];img.alt='';img.className='operation-icon';img.width=28;img.height=28;return img;}
function badge(tone){return el('span',{critical:'Важно',warning:'Внимание',unknown:'Нет данных',ok:'Замер получен'}[tone],'badge '+tone);}
function detail(root,label,value){const p=el('p',null,'small');p.append(el('span',label+': ','muted'),document.createTextNode(value));root.append(p);}
function disclosure(card,key,open){const d=el('details');d.dataset.operation=key;d.open=open.has(key);d.append(el('summary','Подробнее'));card.append(d);return d;}
function balanceCard(b,now,open){
 const card=el('article',null,'account resource-card '+b.tone);card.id='balance-'+b.id;
 const head=el('div',null,'service-top');head.append(icon(b.id==='openrouter'?34:b.id==='digitalocean'?42:27),el('h2',b.title),badge(b.tone));card.append(head);
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
 const head=el('div',null,'service-top');head.append(icon(51),el('h2',m.id==='applications'?'Приложения и бэкапы':m.id),badge(m.tone));card.append(head);
 card.append(el('p',m.message,'resource-message'));
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
function row(item){
 const a=el('a',null,'attention-row '+item.tone);a.href='#'+item.page;
 const body=el('div',null,'row-text');body.append(el('strong',item.title),el('p',item.text,'small'));a.append(icon(item.text.includes('диске')?21:item.tone==='critical'?16:27),body,el('span','›','arrow'));return a;
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
export function renderOperations(snapshot,transportError,now,accounts){
 latest=[snapshot,transportError,now];observation(...latest);
 const ops=snapshot?.operations,balances=sortedBalances(ops,now,transportError),machines=sortedMachines(ops,now,transportError);
 const open=new Set([...document.querySelectorAll('details[data-operation][open]')].map(n=>n.dataset.operation));
 const balancesRoot=$('balances');balancesRoot.replaceChildren(...balances.map(b=>balanceCard(b,now,open)));
 const machineRoot=$('machines');machineRoot.replaceChildren(...machines.map(m=>machineCard(m,now,open)));
 const okay=!transportError&&freshAt(ops?.collected_at,now,1800);
 $('operations-notice').hidden=okay;$('operations-notice').textContent='Нет свежего снимка машин и балансов. Числа не считаются текущими.';
 if(!balances.length)balancesRoot.append(el('p','Данные балансов пока недоступны.','empty'));
 if(!machines.length)machineRoot.append(el('p','Реестр Hermes недоступен. Это не означает отсутствие машин.','empty'));
 const count=ops?.fleet?.inventory_count,enrolled=ops?.fleet?.enrolled;
 $('machine-count').textContent=typeof count==='number'?`${count} записей в реестре · диагностика подключена: ${enrolled} · без свежего состояния: ${machines.filter(m=>m.tone==='unknown').length}`:'Охват машин неизвестен';
 const integrated=integrationRows(snapshot?.integrations,now,transportError);
 for(const page of ['subscriptions','balances','machines']){
  let root=$('integrations-'+page);
  if(!root){root=el('div',null,'accounts');root.id='integrations-'+page;$('page-'+page).append(root);}
  root.replaceChildren(...integrated.filter(r=>r.page===page).map(r=>integrationCard(r,now,open)));
 }
 const attention=integrated.filter(r=>['critical','warning'].includes(r.tone)).map(r=>({page:r.page,tone:r.tone,title:r.title,text:r.problem||'Маленький остаток квоты'}));
 for(const m of machines)if(['critical','warning'].includes(m.tone))attention.push({page:'machines',tone:m.tone,title:m.id==='applications'?'Приложения и бэкапы':m.id,text:m.message+' · '+relativeTime(m.active[0]?.observed_at,now)});
 for(const b of balances)if(['critical','warning'].includes(b.tone))attention.push({page:'balances',tone:b.tone,title:b.title,text:b.problem+' · '+amount(b.amount,b.unit)});
 for(const a of accounts){
  const low=a.view.windows.filter(w=>w.state==='observed'&&[300,10080].includes(w.window_minutes)&&w.remaining<25).sort((x,y)=>x.remaining-y.remaining)[0];
  if(low)attention.push({page:'subscriptions',tone:low.remaining<10?'critical':'warning',title:a.account.login||a.account.label,text:windowLabel(low.window_minutes)+': осталось '+Math.round(low.remaining)+'%'});
  if(a.view.authorizationIssue)attention.push({page:'subscriptions',tone:'warning',title:a.account.login||a.account.label,text:'Нужно восстановить авторизацию'});
 }
 attention.sort((a,b)=>(a.tone==='critical'?0:1)-(b.tone==='critical'?0:1));
 $('attention-count').textContent=attention.length?`${attention.length} записей требуют внимания`:'Подтверждённых проблем в доступных данных нет';
 $('attention-list').replaceChildren(...attention.slice(0,6).map(row));
 const more=$('attention-more');more.hidden=attention.length<=6;$('attention-more-count').textContent=`Ещё ${Math.max(0,attention.length-6)}`;$('attention-rest').replaceChildren(...attention.slice(6).map(row));
 const unknown=balances.filter(b=>b.tone==='unknown').map(b=>({title:b.title,text:b.problem,page:'balances',tone:'unknown'}));
 unknown.push(...machines.filter(m=>m.tone==='unknown').map(m=>({title:m.id,text:m.message,page:'machines',tone:'unknown'})));
 unknown.push(...integrated.filter(r=>r.tone==='unknown').map(r=>({page:r.page,tone:r.tone,title:r.title,text:r.problem})));
 $('unknown-summary').textContent=`Нет подтверждённых данных: ${unknown.length}`;$('unknown-rows').replaceChildren(...unknown.map(row));$('unknown-block').hidden=!unknown.length;
 $('overview-balances').replaceChildren(...balances.map(b=>{const a=el('a',null,'balance-summary '+b.tone);a.href='#balances';a.append(el('span',b.title),el('strong',b.amount===null?'Нет данных':b.billed?'Начислено '+amount(b.amount,b.unit):b.noPrepayment?'Предоплаты нет':amount(b.amount,b.unit)));return a;}));
 $('overview-machines').textContent=typeof count==='number'?`Машины и устройства · ${count} записей →`:'Машины · охват неизвестен →';
}

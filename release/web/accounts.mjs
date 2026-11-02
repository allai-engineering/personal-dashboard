import {renderCockpit} from './cockpit.mjs';
import {initNavigation,renderOperations} from './operations.mjs';
import {number,numeric,emptyMessage} from './model.mjs';
import {snapshotFresh,capacityView} from './limits.mjs';
import {sortedAccounts,relativeTime,dateLabel,windowLabel,remainingDuration,quotaTone} from './account-view.mjs';
const $=id=>document.getElementById(id);
const el=(tag,text,cls)=>{const n=document.createElement(tag);if(text!=null)n.textContent=text;if(cls)n.className=cls;return n;};
let snapshot=null,busy=false,transportError=false;
function timestamp(text,value,cls='muted') {const n=el('p',text,cls);if(value)n.title=dateLabel(value)+' (UTC+3)';return n;}
function detailRow(root,label,value){const row=el('div',null,'detail-row');row.append(el('dt',label),el('dd',value));root.append(row);}
function render(){
 const now=Date.now(),effective=transportError&&snapshot?{...snapshot,cache:{...snapshot.cache,stale:true}}:snapshot;
 const fresh=snapshotFresh(effective,now), all=sortedAccounts(effective,'',now);
 const showSearch=all.length>3; $('search').closest('label').hidden=!showSearch;
 const selected=showSearch?sortedAccounts(effective,$('search').value,now):all;
 const messages=[];
 const unavailable=(snapshot?.external?.sources||[]).filter(s=>s.status!=='ok');
 if(unavailable.length)messages.push('Нет свежих данных: '+unavailable.map(s=>s.title).join(', ')+'.');
 if(transportError)messages.push('Не удалось обновить данные. Текущее состояние не подтверждено.');
 else if(snapshot&&!fresh)messages.push('Снимок устарел. Текущие квоты и ограничения неизвестны.');
 if(snapshot?.demo)messages.push('Демонстрационные данные.');
 if(snapshot&&snapshot.inventory?.status!=='ok')messages.push('Реестр недоступен: список аккаунтов может быть неполным.');
 else if(snapshot&&snapshot.inventory?.complete!==true)messages.push('Реестр получен не полностью.');
 if(snapshot&&snapshot.status!=='ok')messages.push('Некоторые источники данных недоступны.');
 for(const [name,s] of Object.entries(snapshot?.services||{}))if(s.status!=='ok'||s.active_state!=='active')messages.push(`${name}: ${s.active_state||'состояние неизвестно'}`);
 $('notice').hidden=!messages.length;$('notice').textContent=messages.join(' ');
 $('observation').textContent=snapshot?`Снимок ${relativeTime(snapshot.observed_at_utc,now)}`:transportError?'Снимок недоступен':'Получаем данные…';
 $('observation').title=snapshot?dateLabel(snapshot.observed_at_utc)+' (UTC+3)':'';
 const complete=snapshot?.inventory?.status==='ok'&&snapshot.inventory.complete===true;
 const affected=all.filter(x=>!x.view.authorizationIssue&&x.view.problems.length).length, failed=all.filter(x=>x.view.failures?.failed>0).length,authCount=all.filter(x=>x.view.authorizationIssue).length;
 $('account-count').textContent=(complete?`${all.length} аккаунтов`:'Полнота списка неизвестна')+(fresh&&affected?` · С ограничениями: ${affected}`:'')+(fresh&&failed?` · С ошибками попыток: ${failed}`:'')+(authCount?` · С проблемами авторизации: ${authCount}`:'');
 const open=new Set([...document.querySelectorAll('.account details[open]')].map(n=>n.dataset.id));
 const cards=$('accounts'),authCards=$('authorization-accounts');cards.replaceChildren();authCards.replaceChildren();
 $('authorization-section').hidden=!selected.some(x=>x.view.authorizationIssue);
 if(!selected.length)cards.append(el('p',emptyMessage(snapshot,Boolean($('search').value)),'empty'));
 for(const {account:a,view:v} of selected){
  const card=el('article',null,'account'),head=el('div',null,'account-head'),identity=el('div');
  const details=el('details');details.dataset.id=a.id;details.open=open.has(a.id);details.append(el('summary','Подробнее'));
  card.dataset.accountId=a.id;card.setAttribute('aria-label',a.login||a.label);
  identity.append(el('h2',a.login||a.label));
  details.append(el('p',a.source_titles.join(' · '),'muted small'));
  if(a.provider==='openai'||a.provider==='codex')details.append(el('p','ChatGPT + Codex · ниже квота Codex','muted small'));
  if(a.inventory_present===false)details.append(el('p','Без привязки к реестру','muted'));
  const plan=a.subscription?.plan;
  const provider=a.provider==='claude'?'Claude':'OpenAI';
  head.append(identity,el('span',provider+' · '+(plan?plan[0].toUpperCase()+plan.slice(1):'тариф неизвестен'),plan?'plan':'plan unknown'));card.append(head);
  const quotas=el('div',null,'quotas');card.append(quotas);
  for(const w of v.windows.length?v.windows:[{state:'unknown'}]){
   const tone=quotaTone(w),block=el('div',null,'quota'+(tone?' quota-'+tone:''));
   block.append(el('p',(w.window_minutes===10080?'Неделя':w.window_minutes===300?'5 часов':windowLabel(w.window_minutes))+(w.slot==='seven_day_opus'?' · Opus':w.slot==='seven_day_sonnet'?' · Sonnet':''),'quota-label'));
   const line=el('div',null,'quota-line');line.append(el('strong',w.state==='observed'?number(w.remaining)+'%':w.state==='old'?'Нет свежего замера':'Нет данных о квоте',w.state==='observed'?'amount':'amount unknown'),el('span',w.state==='observed'?'осталось':'','muted'));block.append(line);
   if(w.state==='observed'){const progress=el('progress');progress.max=100;progress.value=w.remaining;progress.setAttribute('aria-label',windowLabel(w.window_minutes)+': осталось '+number(w.remaining)+'%');block.append(progress);}
   const quotaInfo=el('div',null,'quota-info');quotaInfo.append(el('p',windowLabel(w.window_minutes)+(w.slot==='seven_day_opus'?' · Opus':w.slot==='seven_day_sonnet'?' · Sonnet':''),'small'));
   if(tone)quotaInfo.append(el('p',tone==='critical'?'Почти исчерпана':'Мало осталось','warning small'));
   if(w.state==='old')quotaInfo.append(el('p',`Последний: ${number(w.previous)}% · ${relativeTime(a.quota?.observed_at,now)}`,'warning small'));
   if(w.reset_at){
    if(w.state==='observed')block.append(timestamp(`Сброс через ${remainingDuration(w.reset_at,now)}`,w.reset_at,'reset'));
    quotaInfo.append(timestamp(`${w.state==='observed'?'Сброс: ':'Последний срок сброса: '}${dateLabel(w.reset_at)}`,w.reset_at,'muted small'));
    if(w.state!=='observed')block.append(el('p','Сброс не подтверждён','muted small'));
   }
   else block.append(el('p','Сброс неизвестен','muted small'));
   if(w.state!=='old')quotaInfo.append(timestamp(a.quota?.observed_at?`Замер ${relativeTime(a.quota.observed_at,now)}`:'Свежих наблюдений нет',a.quota?.observed_at,'muted small'));
   details.append(quotaInfo);
   quotas.append(block);
  }
  const subscription=el('p',null,'subscription');
  const until=a.subscription?.active_until,left=remainingDuration(until,now);
  subscription.append(el('span',left?`Подписка ещё на ${left}`:until?'Срок подписки требует обновления':'Срок подписки неизвестен'));
  if(until)subscription.append(el('span',`${dateLabel(until)} · по сохранённым данным`,'muted small'));
  details.append(subscription);
  if(v.problems.length||(!v.stateKnown&&(!a.source_id||!v.fresh||!v.windows.some(w=>w.state==='observed')))){
   const state=el('p',v.status,'state '+v.tone);details.append(state);
   if(v.problems[0]?.until)details.append(timestamp(`До ${dateLabel(v.problems[0].until)}`,v.problems[0].until,'warning small'));
  }
  if(v.failures?.failed>0)details.append(el('p',`Ошибки попыток: ${number(v.failures.failed)} из ${number(v.failures.total)} за 15 мин`,'attempt-errors'));
  const dl=el('dl');detailRow(dl,'Идентификатор',a.label);detailRow(dl,'Источник тарифа',plan?(a.hostkey?'Запись авторизации CPA':'Данные подключения / сервиса'):'Нет данных');
  if(a.source_id)detailRow(dl,'Последняя проверка источника',dateLabel(a.source_observed_at));
  for(const c of a.connections||[])if(c.problem)detailRow(dl,c.title,c.problem);
  if(a.provider==='openai'||a.provider==='codex')detailRow(dl,'Лимиты чатов ChatGPT','Отдельно не измерены');
  detailRow(dl,'Текущий RPM','Неизвестно');detailRow(dl,'Лимит RPM',numeric(a.rpm_limit)?a.rpm_limit===0?'Без лимита':number(a.rpm_limit)+' / мин':'Неизвестно');detailRow(dl,'Занятость аккаунта','Неизвестно');
  const c=a.hostkey?snapshot?.runtime?.concurrency:null;detailRow(dl,'Concurrency / warm',a.inventory_present!==false&&numeric(c?.max_concurrency)?number(c.max_concurrency)+' / '+number(c.warm_reserved_slots):'Неизвестно');details.append(dl);
  for(const p of v.problems)details.append(el('p',p.text+(p.model?' · '+p.model:'')+(p.until?' · до '+dateLabel(p.until):''),'warning small'));
  for(const [key,label] of [['15','15 минут'],['60','Час'],['1440','Сутки']]){const m=a.windows?.[key];details.append(el('p',m?`${label}: ${number(m.failed)} ошибок / ${number(m.attempt_records)} записей попыток${v.fresh?'':' · старый снимок'}`:`${label}: статистика неизвестна`,'small'));if(m&&Object.keys(m.status_codes||{}).length)details.append(el('p','Коды: '+Object.entries(m.status_codes).map(([code,n])=>`${code} × ${number(n)}`).join(', '),'muted small'));}
  details.append(el('p','Ошибка попытки не равна сбою запроса: повтор мог завершиться успешно. Коды Keeper не различают upstream и локальный отказ. Отсутствие ограничений CPA не гарантирует успешную генерацию.','muted small'));card.append(details);(v.authorizationIssue?authCards:cards).append(card);
 }
 const resources=renderOperations(effective,transportError,now);
 renderCockpit(effective,all,resources,now,transportError);
 const cap=fresh?capacityView(snapshot?.runtime):null;
 $('capacity').textContent=cap?`В выборке плагина занято ${number(cap.used)} из ${number(cap.limit)} слотов. Охват: ${number(cap.count)} из ${number(snapshot?.inventory?.listed_accounts)} аккаунтов; это не общая свободная ёмкость.`:'Общая текущая занятость неизвестна: нет пригодного полного измерения.';
 const p=snapshot?.runtime?.policy;
 $('policy').textContent=`Настройки в снимке: ожидание ${number(p?.['max-retry-interval'])} с · таймер начала ответа ${p?.stream_start_timeout||'неизвестен'} · cooldown ${number(p?.['transient-error-cooldown-seconds'])} с.`;
}
async function load(manual=false){
 if(busy)return;busy=true;$('refresh').disabled=true;
 const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),15000);
 try{const r=await fetch(manual?'/api/refresh':'/api/snapshot',{cache:'no-store',signal:controller.signal});if(r.status===401){location.replace('/');return;}if(!r.ok)throw Error();const s=await r.json();if(s.schema!=='cpa-account-dashboard-v1'||!Array.isArray(s.accounts))throw Error();snapshot=s;transportError=false;}
 catch{transportError=true;}
 finally{clearTimeout(timer);busy=false;$('refresh').disabled=false;render();}
}
initNavigation();
addEventListener('hashchange',render);
$('refresh').addEventListener('click',()=>load(true));$('search').addEventListener('input',render);
setInterval(()=>{if(!document.hidden)load();},60000);
setInterval(()=>{if(snapshot&&!document.hidden&&!document.activeElement?.closest('.account,.cockpit-ledger,#evidence-content'))render();},15000);
document.addEventListener('visibilitychange',()=>{if(!document.hidden)load();});load();

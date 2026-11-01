import {numeric, accountRows} from './model.mjs';
import {snapshotFresh, quotaView, accountProblems} from './limits.mjs';
const generalWeekly=w=>w.window_minutes===10080&&!['seven_day_opus','seven_day_sonnet'].includes(w.slot);
const authorizationMessages=new Set(['Сессия Claude истекла','Ошибка авторизации CPA','Нет доступа к данным квот','Нет доступа к авторизации на устройстве','Нужна повторная авторизация','Ошибка авторизации']);
export function quotaTone(w) {
 if(w.state!=='observed'||![300,10080].includes(w.window_minutes)||!numeric(w.remaining)||w.remaining>100)return '';
 return w.remaining<10?'critical':w.remaining<25?'low':'';
}

export function accountView(account, snapshot, now=Date.now()) {
  const sourceAge=now-Date.parse(account.source_observed_at);
  const fresh=account.source_id?(!snapshot?.cache?.stale&&account.source_status==='ok'&&sourceAge>=0&&sourceAge<900000):snapshotFresh(snapshot,now);
  const quotaAge=now-Date.parse(account.source_id?account.source_observed_at:snapshot?.observed_at_utc);
  const quotaFresh=!snapshot?.cache?.last_error&&Number.isFinite(quotaAge)&&quotaAge>=0&&quotaAge<90000000&&(!account.source_id||account.source_status==='ok');
  const windows=(account.quota?.windows||[]).map(w=>({...w,...quotaView(account.quota,w,quotaFresh,now)})).sort((a,b)=>Number(generalWeekly(b))-Number(generalWeekly(a)));
  const weekly=windows.filter(w=>generalWeekly(w)&&w.state==='observed');
  const weeklyRemaining=weekly.length?Math.min(...weekly.map(w=>w.remaining)):null;
  const problems=fresh?accountProblems(account,now):[];
  if(fresh&&account.data_problem)problems.unshift({severity:'warning',text:account.data_problem});
  if(windows.some(w=>w.state==='observed'&&w.remaining===0))problems.push({severity:'warning',text:'Наблюдаемая квота исчерпана'});
  const recent=account.windows?.['15'];
  const failures=fresh&&numeric(recent?.failed)&&numeric(recent?.attempt_records)?{failed:recent.failed,total:recent.attempt_records}:null;
  const stateKnown=fresh&&account.inventory_present!==false&&account.cooldowns?.status==='ok'&&account.disabled===false&&account.unavailable===false&&account.status==='active';
  const tone=problems.length?'warning':failures?.failed>0?'warning':stateKnown?'neutral':'unknown';
  const status=problems.length?problems[0].text:!stateKnown?(account.source_id?(fresh?'Источник не подтверждает состояние аккаунта':'Нет свежих данных источника'):'Состояние неизвестно'):failures?.failed>0?'Есть ошибки попыток':'Ограничений CPA не отмечено';
  const rank=problems.length?0:failures?.failed>0?1:!stateKnown?2:3;
  const authorizationIssue=authorizationMessages.has(account.data_problem)||problems.some(p=>authorizationMessages.has(p.text));
  return {fresh,windows,problems,failures,stateKnown,tone,status,rank,weeklyRemaining,authorizationIssue};
}
export function sortedAccounts(snapshot,query='',now=Date.now()) {
 const needle=query.trim().toLocaleLowerCase('ru');
 return accountRows(snapshot).filter(a=>`${a.label} ${a.login||''} ${a.provider} ${a.subscription?.plan||''} ${(a.source_titles||[]).join(' ')}`.toLocaleLowerCase('ru').includes(needle)).map(account=>({account,view:accountView(account,snapshot,now)})).sort((a,b)=>(a.view.weeklyRemaining??Infinity)-(b.view.weeklyRemaining??Infinity)||a.view.rank-b.view.rank||String(a.account.label).localeCompare(String(b.account.label),'ru'));
}
export function relativeTime(value,now=Date.now()) {
 const age=now-Date.parse(value);
 if(!Number.isFinite(age)||age<0)return 'Время неизвестно';
 if(age<60000)return 'менее минуты назад';
 if(age<3600000)return `${Math.floor(age/60000)} мин назад`;
 if(age<86400000)return `${Math.floor(age/3600000)} ч назад`;
 return `${Math.floor(age/86400000)} дн. назад`;
}
export function dateLabel(value) {
 return Number.isFinite(Date.parse(value))?new Intl.DateTimeFormat('ru-RU',{day:'numeric',month:'long',hour:'2-digit',minute:'2-digit',timeZone:'Europe/Istanbul'}).format(new Date(value)):'Дата неизвестна';
}
export function windowLabel(minutes) {
 if(minutes===10080)return 'Недельная квота';
 if(minutes===300)return 'Квота на 5 часов';
 if(!numeric(minutes)||minutes===0)return 'Остаток квоты';
 return minutes%1440===0?`Квота на ${minutes/1440} дн.`:minutes%60===0?`Квота на ${minutes/60} ч`:`Квота на ${minutes} мин`;
}

export function remainingDuration(value,now=Date.now()) {
 const ms=Date.parse(value)-now;
 if(!Number.isFinite(ms)||ms<=0)return null;
 const minutes=Math.ceil(ms/60000),days=Math.floor(minutes/1440),hours=Math.floor(minutes%1440/60);
 if(days){
  const word=new Intl.PluralRules('ru').select(days);
  return `${days} ${{one:'день',few:'дня',many:'дней',other:'дня'}[word]}`+(hours?` ${hours} ч`:'');
 }
 if(hours)return `${hours} ч`+(minutes%60?` ${minutes%60} мин`:'');
 return `${minutes} мин`;
}

import {freshAt} from './operations-view.mjs';
import {dateLabel,relativeTime} from './account-view.mjs';
const el=(tag,text,cls)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;};
const mailboxLabel=id=>id.startsWith('google-')?'Gmail · '+id.slice(7):id==='yandex'?'Яндекс':id;
export function mailView(data,now,transportError=false){
 const fresh=!transportError&&freshAt(data?.checked_at,now,90000);
 const gaps=(data?.coverage||[]).filter(c=>c.status!=='ok'||!c.history_complete);
 const rows=(data?.records||[]).map(r=>{
  const sourceAt=r.sources.reduce((latest,s)=>s.date>latest?s.date:latest,'');
  const access=r.sources.some(s=>data.coverage.some(c=>c.mailbox===s.mailbox&&['ok','partial'].includes(c.status)));
  const stale=!fresh||!access;
  const upcoming=r.renewal_date&&r.renewal_date>=new Date(now).toISOString().slice(0,10)?r.renewal_date:null;
  return {...r,stale,sourceAt,upcoming,tone:stale?'unknown':r.status==='payment_failed'?'warning':'ok'};
 }).sort((a,b)=>(a.tone==='warning'?-1:0)-(b.tone==='warning'?-1:0)||(a.upcoming||'9999').localeCompare(b.upcoming||'9999')||a.service.localeCompare(b.service));
 return {rows,notice:!fresh?'Проверка почты недоступна или устарела. Ниже — прежние сведения.':gaps.length?'Охват неполный: часть истории ещё проверяется или источник недоступен.':'Ежедневная проверка выполнена. Письма подтверждают сведения на дату источника, а не текущее состояние сервиса.'};
}
export function renderMail(data,now,transportError=false){
 let section=document.getElementById('mail-subscriptions');
 if(!section){section=el('section');section.id='mail-subscriptions';section.setAttribute('aria-label','Платные сервисы из почты');document.getElementById('page-balances').append(section);}
 const open=new Set([...section.querySelectorAll('details[open]')].map(d=>d.dataset.mail));
 const view=mailView(data,now,transportError);
 section.replaceChildren(el('h2','Подписки и платежи из почты'),el('p',view.notice,'muted small'));
 const grid=el('div',undefined,'accounts');section.append(grid);
 if(!view.rows.length)grid.append(el('p','Подтверждённых записей пока нет. Это не означает отсутствие подписок.','muted small'));
 for(const r of view.rows){
  const card=el('article',undefined,'account resource-card '+r.tone);card.dataset.mailId=r.id;card.append(el('h3',r.service));
  const label={last_payment:'Последний платёж',next_charge:'Следующее списание',invoice_due:'Счёт к оплате',unknown:'Сумма неизвестна'}[r.amount_kind];
  card.append(el('p',r.amount===null?'Сумма неизвестна':`${label}: ${r.amount} ${r.currency}`,'small'));
  const date=r.renewal_date;
  card.append(el('p',date?`${r.upcoming?'Продление':'Указанная дата продления уже прошла'}: ${date}`:'Дата продления неизвестна','small'));
  if(r.status!=='observed')card.append(el('p',r.status==='cancelled'?'Есть письмо об отмене':'Есть письмо об ошибке оплаты','small'));
  if(r.stale)card.append(el('p','Проверка источника не подтверждена','small'));
  card.append(el('p','Письмо '+relativeTime(r.sourceAt,now),'muted small'));
  const d=el('details');d.dataset.mail=r.id;d.open=open.has(r.id);d.append(el('summary','Источники'));
  for(const s of r.sources){
   const p=el('p',undefined,'small');const title=mailboxLabel(s.mailbox)+' · '+dateLabel(s.date);
   if(s.url){const a=el('a',title);a.href=s.url;a.target='_blank';a.rel='noopener noreferrer';p.append(a);}else p.append(document.createTextNode(title));
   const fields=(s.fields||[]).map(f=>({amount:'сумма',renewal:'продление',status:'статус'}[f])).join(', ');
   p.append(el('span',' · '+s.ref.slice(0,8)+(fields?' · '+fields:''),'muted'));d.append(p);
  }
  d.append(el('p','Чек не подтверждает автопродление или текущий баланс. Разные валюты не складываются. Тексты писем не публикуются.','muted small'));
  card.append(d);grid.append(card);
 }
}

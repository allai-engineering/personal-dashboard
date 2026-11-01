import {numeric} from './model.mjs';
export function snapshotFresh(s, now=Date.now()) {
 const age=now-Date.parse(s?.observed_at_utc);
 return !s?.cache?.stale && Number.isFinite(age) && age>=0 && age<120000;
}
export function quotaView(q,w,fresh,now=Date.now()) {
 const age=now-Date.parse(q?.observed_at), remaining=w?.remaining_percent, reset=Date.parse(w?.reset_at);
 if(!numeric(remaining)||remaining>100||!numeric(w?.window_minutes)||w.window_minutes<=0) return {state:'unknown',remaining:null};
 if(!fresh||!Number.isFinite(age)||age<0||age>=90000000||(Number.isFinite(reset)&&reset<=now)) return {state:'old',remaining:null,previous:remaining};
 return {state:'observed',remaining};
}
export const reasons={quota:'Квота upstream',credential_quota:'Квота аккаунта',cloudflare_challenge:'Проверка Cloudflare',invalid_grant:'Нужна повторная авторизация',unauthorized:'Ошибка авторизации',payment_required:'Требуется оплата',not_found:'Ресурс не найден',model_not_supported:'Модель не поддерживается',transient_error:'Временная ошибка',unknown:'Причина не передана'};
export function accountProblems(a,now=Date.now()) {
 const items=[];
 if(a.disabled===true||a.status==='disabled')items.push({severity:'muted',text:'Аккаунт отключён в CPA'});
 for(const c of a.cooldowns?.items||[])if(Date.parse(c.retry_at)>now)items.push({severity:'warning',text:reasons[c.reason]||reasons.unknown,until:c.retry_at,model:c.model,scope:c.scope});
 if(!items.length&&Date.parse(a.next_retry_at)>now)items.push({severity:'warning',text:'Действует ограничение CPA',until:a.next_retry_at});
 if(!items.length&&(a.status==='error'||a.unavailable===true))items.push({severity:'error',text:'CPA отмечает ошибку или недоступность. Причина не передана.'});
 return items;
}
export function capacityView(r) {
 const c=r?.capacity;
 if(r?.sources?.capacity?.status!=='ok'||!c||c.stale!==false||c.error_present===true||!['available','connected'].includes(c.authority_state)||!numeric(c.in_flight)||!numeric(c.limit)||!numeric(c.listed_accounts)||c.listed_accounts===0)return null;
 return {used:c.in_flight,limit:c.limit,count:c.listed_accounts};
}

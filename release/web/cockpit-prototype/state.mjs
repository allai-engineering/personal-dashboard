// THROWAWAY: fixture-only state and bounded presentation experiment; no services or persistence.
export const variants={A:'Сводка',B:'Лента',C:'Панель'};
export const initial=()=>({seen:{},ack:{},recovered:false,stale:false,worsened:false,task:'running',review:'auto',plan:'standard'});
export function issues(s){return [
 {id:'access',title:'Восстановить доступ',domain:'Аккаунты',tone:s.worsened?'critical':'warning',urgent:s.worsened,version:s.worsened?2:1,body:'Квота демо-аккаунта недоступна. Для проверки нужен вход.',why:'Актуальный остаток неизвестен; это не свободный лимит.',owner:'Вы',when:s.worsened?'Нужно сегодня':'Срок не задан',observed:'2 ноября, 14:10',next:'Посмотреть требование входа',history:['Вчера: чтение квоты работало','14:10: сессия истекла','14:20: нового подтверждённого замера нет']},
 {id:'backup',title:'Резервная копия не подтверждена',domain:'Машины',tone:'critical',urgent:true,version:1,body:s.stale?'Последняя проверка устарела. Текущее состояние неизвестно.':'Последняя проверка резервной копии завершилась ошибкой.',why:'Нет подтверждения, что актуальные данные можно восстановить.',owner:'Ответственный не подтверждён',when:'Проверить сегодня',observed:'2 ноября, 13:55',next:'Разобраться в проверке',history:['1 ноября: восстановление подтверждено','13:55: проверка копии завершилась ошибкой',s.stale?'14:20: сведения устарели; восстановления не подтверждено':'14:15: успешного восстановления ещё не подтверждено']}
 ].filter(i=>!(s.recovered&&i.id==='backup'));}
export function apply(s,action){const n={...s,seen:{...s.seen},ack:{...s.ack}};
 if(action.type==='seen')n.seen[action.id]=issues(s).find(i=>i.id===action.id)?.version;
 if(action.type==='ack')n.ack[action.id]=true;
 if(action.type==='stale')n.stale=true;
 if(action.type==='worsen')n.worsened=true;
 if(action.type==='recover'){n.recovered=true;n.stale=false;}
 if(action.type==='task')n.task=action.value;
 if(action.type==='review')n.review=action.value;
 if(action.type==='plan')n.plan=action.value;
 return n;
}
export function compact(issue,s){return !issue.urgent&&s.seen[issue.id]===issue.version;}
export function taskView(s){return ({running:{status:'Выполняется',tone:'ok',progress:'14:18 · живое выполнение подтверждено',checkpoint:'14:30 · плановая контрольная точка',origin:'Ручной повтор',coverage:'Частичный результат',intervention:'Если повтор потребует входа или остановится без нового прогресса'},planned:{status:'Запланировано',tone:'unknown',progress:'Выполнение ещё не началось',checkpoint:'Следующий рабочий запуск · дата в демо не задана',origin:'Плановое задание',coverage:'Новых результатов нет',intervention:'Сейчас действие не требуется'},stalled:{status:'Прогресс не подтверждён',tone:'warning',progress:'Последнее подтверждение 13:20 · устарело',checkpoint:'Следующая проверка не подтверждена',origin:'Ручной повтор',coverage:'Частичный результат',intervention:'Нужна проверка, кто продолжает выполнение'},recovered:{status:'Завершено вручную',tone:'ok',progress:'14:19 · ручной запуск завершён',checkpoint:'Следующий плановый запуск',origin:'Ручной повтор',coverage:'Частичный результат',intervention:'Прочитать непроверенные источники; исходный плановый сбой остаётся в истории'}})[s.task];}
const allowed={access:new Set(['access-observation','access-history']),backup:new Set(['backup-observation','backup-history']),task:new Set(['task-execution','task-domain','task-history']),hearing:new Set(['hearing-observation'])};
const binding={'access-observation':'evidence_detail','access-history':'history','backup-observation':'evidence_detail','backup-history':'history','task-domain':'evidence_detail','task-execution':'task_status','task-history':'history','hearing-observation':'evidence_detail'};
export function validPlan(p,focus){
 if(!Object.hasOwn(allowed,focus)||!p||typeof p!=='object'||Array.isArray(p)||Object.keys(p).sort().join(',')!=='blocks,focus_id,schema,snapshot_id'||p.schema!=='cockpit-view-plan-v1'||p.snapshot_id!=='synthetic-1'||p.focus_id!==focus||!Array.isArray(p.blocks)||!p.blocks.length||p.blocks.length>4)return false;
 const seen=new Set();
 return p.blocks.every(b=>!!b&&typeof b==='object'&&!Array.isArray(b)&&Object.keys(b).sort().join(',')==='component,record_ids'&&Array.isArray(b.record_ids)&&b.record_ids.length>0&&b.record_ids.length<=4&&b.record_ids.every(id=>typeof id==='string'&&allowed[focus].has(id)&&binding[id]===b.component&&!seen.has(id)&&seen.add(id)));
}
export function planFor(focus,mode){if(mode==='unavailable')return null;return {schema:'cockpit-view-plan-v1',snapshot_id:'synthetic-1',focus_id:focus,blocks:[{component:mode==='invalid'?'execute_shell':'evidence_detail',record_ids:[focus==='task'?'task-domain':focus+'-observation']},{component:'history',record_ids:[focus+'-history']}]};}
export function selfCheck(){const check=(v,m)=>{if(!v)throw Error(m);};let s=initial();s=apply(s,{type:'seen',id:'backup'});check(!compact(issues(s).find(i=>i.id==='backup'),s),'Urgent survives seen');s=apply(s,{type:'seen',id:'access'});check(compact(issues(s)[0],s),'Seen nonurgent compacts');s=apply(s,{type:'worsen'});check(!compact(issues(s)[0],s),'Worsening expands');s=apply(s,{type:'stale'});check(issues(s).some(i=>i.id==='backup'),'Stale does not resolve');check(!validPlan(planFor('access','invalid'),'access'),'Invalid plan rejected');check(validPlan(planFor('access','valid'),'access'),'Bounded plan accepted');check(!validPlan({...planFor('access','valid'),snapshot_id:'wrong'},'access'),'Wrong snapshot rejected');check(!validPlan({schema:'cockpit-view-plan-v1',snapshot_id:'synthetic-1',focus_id:'access',blocks:[null]},'access'),'Null block rejected');return true;}

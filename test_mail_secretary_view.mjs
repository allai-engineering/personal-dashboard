import assert from 'node:assert/strict';
import {secretaryView,outcomeLabels} from './release/web/mail-secretary.mjs';
assert.deepEqual(outcomeLabels({}),{result:'Ожидаемый результат: не определён',actor:'Следующий шаг за: пока неизвестно'});
const waiting={expected_result:'receive_material',next_actor:'counterparty',owner:'mail-secretary',state:'waiting'};
assert.deepEqual(outcomeLabels(waiting),{result:'Ожидаемый результат: получить материал',actor:'Следующий шаг за: собеседником'});
assert.deepEqual(outcomeLabels(waiting,{status:'resolved'}),{result:'Ожидавшийся результат: получить материал',actor:'Следующий шаг не требуется: вы закрыли дело. Выполнение по переписке не подтверждено.'});
const now=Date.parse('2026-11-04T10:00:00Z');
assert.equal(secretaryView(null,now).counts,null);
const data={checked_at:new Date(now).toISOString(),run_state:'running',case_counts:{needs_user:0,waiting:1,done:0},cases:[{state:'waiting'}]};
assert.equal(secretaryView(data,now).running,true);
assert.equal(secretaryView(data,now+601e3).running,false);
assert.equal(secretaryView(data,now,true).running,false);
assert.match(secretaryView(data,now+601e3).notice,/мог прерваться/);
assert.equal(secretaryView(data,now+27*3600e3).fresh,false);
console.log('mail secretary: unknown counts and expired active-run claims passed');

const {backlogLabel}=await import('./release/web/mail-secretary.mjs');
assert.match(backlogLabel({}),/Возраст очереди неизвестен/);
assert.match(backlogLabel({pending:3,checked_at:'2026-11-05T12:00:00Z',backlog:{oldest_at:'2026-11-01T12:00:00Z',unknown_age:1,reasons:{source_unavailable:1,unattempted:2}}}),/4 дн.*Без даты.*1.*источник недоступен: 1/);

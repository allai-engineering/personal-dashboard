import assert from 'node:assert/strict';
import {secretaryView} from './release/web/mail-secretary.mjs';
const now=Date.parse('2026-11-04T10:00:00Z');
assert.equal(secretaryView(null,now).counts,null);
const data={checked_at:new Date(now).toISOString(),run_state:'running',case_counts:{needs_user:0,waiting:1,done:0},cases:[{state:'waiting'}]};
assert.equal(secretaryView(data,now).running,true);
assert.equal(secretaryView(data,now+601e3).running,false);
assert.equal(secretaryView(data,now,true).running,false);
assert.match(secretaryView(data,now+601e3).notice,/мог прерваться/);
assert.equal(secretaryView(data,now+27*3600e3).fresh,false);
console.log('mail secretary: unknown counts and expired active-run claims passed');

// The same canonical projection drives the owner queue and the remaining mail lanes.
const {secretaryCases}=await import('./release/web/mail-secretary.mjs');
const stamp=new Date(now).toISOString();
const first={id:'a',kind:'reply_needed',state:'needs_user',service:'google'},second={...first,id:'b'};
const projection={checked_at:stamp,run_state:'partial',case_counts:{needs_user:2,waiting:1,done:0},cases:[first,first,second,{...first,id:'c',kind:'waiting_reply',state:'waiting'}],pending:0,omitted_cases:0,coverage:{ok:1,partial:0,unavailable:0}};
const control={available:true,decisions:{}};
assert.deepEqual(secretaryCases(projection,now,false,control).owners.map(r=>r.id),['a','b']);
assert.equal(secretaryCases(projection,now,false,control).limitations.length,0);
for(const status of ['snoozed','resolved','queued','running','blocked']){
 const result=secretaryCases(projection,now,false,{available:true,decisions:{a:{status}}});
 assert.deepEqual(result.owners.map(r=>r.id),['b']);
}
assert.deepEqual(secretaryCases(projection,now,false,{available:true,decisions:{a:{status:'cancelled',reason:'reply_received'},c:{status:'due'}}}).owners.map(r=>r.id),['a','b','c']);
assert.ok(secretaryCases(projection,now+27*3600e3,false,control).limitations.length);
assert.ok(secretaryCases({...projection,omitted_cases:3},now,false,control).limitations.some(s=>s.includes('не вошла')));
assert.ok(secretaryCases(null,now,false,null).limitations.length);
console.log('Canonical mail owner eligibility, identity, replay and coverage passed');

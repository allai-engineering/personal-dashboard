import assert from 'node:assert/strict';
import {batteryView} from './release/web/operations.mjs';
const now=Date.now(),stamp=new Date(now).toISOString();
const m={kind:'physical_mac',state:'not_enrolled',battery:{status:'ok',observed_at:stamp,checked_at:stamp,charge_percent:100,health_percent:89,health_condition:'normal',cycle_count:0,limit_status:'ok',limit_percent:80,limit_enabled:true}};
assert.equal(batteryView(m,now).label,'Лимит 80% подтверждён');assert.equal(batteryView(m,now).charge,100);
assert.equal(batteryView(m,now).health,89);assert.equal(batteryView(m,now).tone,'ok');
for(const status of ['unreachable','not_connected','unavailable']){const v=batteryView({...m,battery:{...m.battery,status}},now);assert.equal(v.tone,'unknown');assert.equal(v.charge,null);assert.match(v.label,/80% не подтверждены/);}
for(const field of ['observed_at','checked_at']){
 const v=batteryView({...m,battery:{...m.battery,[field]:new Date(now-1800e3).toISOString()}},now);assert.equal(v.fresh,false);assert.equal(v.health,null);
}
assert.equal(batteryView(m,now,true).tone,'unknown');
assert.equal(batteryView({...m,battery:{...m.battery,limit_enabled:false}},now).tone,'warning');
assert.match(batteryView({...m,battery:{...m.battery,limit_status:'unsupported'}},now).label,/неизвестен/);
assert.equal(batteryView({...m,battery:{...m.battery,charge_percent:0,health_percent:0}},now).charge,0);
assert.equal(batteryView({kind:'physical_mac'},now).tone,'unknown');
console.log('Battery view: fresh native limit, independent health, disabled/unknown/stale/transport and real zero checks passed');

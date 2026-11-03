// Reuse the displayed evidence model so task identities and freshness cannot drift.
import {sortedAccounts} from './web/account-view.mjs';
import {sortedMachines,sortedBalances} from './web/operations-view.mjs';
import {integrationRows} from './web/integrations-view.mjs';
import {overview} from './web/cockpit-view.mjs';
export function intake(snapshot,now=Date.now()){
 const resources={machines:sortedMachines(snapshot.operations,now),balances:sortedBalances(snapshot.operations,now),integrated:integrationRows(snapshot.integrations,now)};
 return overview(snapshot,sortedAccounts(snapshot,'',now),resources,now,false).records.map(r=>({record_id:r.id,subject:r.title,condition_key:r.condition_key||JSON.stringify([r.state,r.reason,r.value]),source_state:r.state,source_at:r.observedAt||new Date(now).toISOString()}));
}
if(process.argv[1]?.endsWith('/incident_intake.mjs')){
 let raw='';for await(const part of process.stdin){raw+=part;if(raw.length>8*1024*1024)throw Error('size');}
 process.stdout.write(JSON.stringify(intake(JSON.parse(raw))));
}

import assert from 'node:assert/strict';
import {overview,reconcile,compact} from './release/web/cockpit-view.mjs';

const now=Date.parse('2026-11-02T12:00:00Z'),stamp=new Date(now).toISOString();
const issue={id:'quota-a',state:'open',tone:'warning',value:20,reason:'quota',observedAt:stamp,title:'Synthetic quota'};
let active=reconcile(new Map(),[issue]);
const seen=new Map([['quota-a',active.get('quota-a').revision]]);
assert.equal(compact(active.get('quota-a'),seen),true);
active=reconcile(active,[{...issue,observedAt:'2026-11-02T12:01:00Z'}]);
assert.equal(compact(active.get('quota-a'),seen),true,'a new receipt is not a new problem');
assert.equal(compact(reconcile(new Map(),[issue]).get('quota-a'),seen),true,'seen revision survives rebuilding from a snapshot');
active=reconcile(active,[{...issue,value:19}]);
assert.equal(compact(active.get('quota-a'),seen),false,'worsening re-escalates');
active=reconcile(active,[{...issue,state:'unknown'}]);
assert.equal(active.get('quota-a').unconfirmed,true);
assert.equal(active.get('quota-a').tone,'warning');
active=reconcile(active,[{...issue,state:'clear'}]);
assert.equal(active.size,0,'explicit fresh recovery clears');
active=reconcile(new Map(),[{...issue,tone:'critical'}]);
assert.equal(compact(active.get('quota-a'),new Map([['quota-a',1]])),false,'urgent never compacts');

const snapshot={observed_at_utc:stamp,cockpit:{collected_at:stamp,court:{status:'partial',observed_at:stamp,
 receipt_status:'ok',receipt_scope:'kad_metadata',receipt_observed_at:stamp,changes:0,important:0,
 unverified:1,carried_forward:2,search_status:'incomplete',confirmed_dates_available:false},tasks:[
 {id:'scheduled',profile:'lawyer',label:'Synthetic court check',state:'failed',origin:'scheduled',claimed_at:stamp,
  observed_at:stamp,progress_at:null,liveness:'not_applicable',next_run_at:null,enabled:true},
 {id:'manual',profile:'lawyer',label:'Synthetic court check',state:'completed',origin:'manual',claimed_at:stamp,
  observed_at:stamp,progress_at:null,liveness:'not_applicable',next_run_at:null,enabled:true},
 {id:'unverified',profile:'ops',label:'Synthetic task',state:'running',origin:'scheduled',claimed_at:stamp,
  observed_at:stamp,progress_at:null,liveness:'unverified',next_run_at:null,enabled:true}],profiles:[],events:[]}};
const view=overview(snapshot,[],{balances:[],machines:[],integrated:[]},now,false);
assert.equal(view.records.find(r=>r.id==='court-coverage').state,'open');
assert.equal(view.records.find(r=>r.id==='court-coverage').tone,'warning');
assert.equal(view.activeTasks.length,0,'stored running is not verified active');
assert.equal(view.tasks.length,3,'scheduled failure and manual success both remain');
assert.equal(view.events.length,0,'unknown hearing dates do not become events');
const stale=overview(snapshot,[],{balances:[],machines:[],integrated:[]},now+180001,false);
assert.equal(stale.activeTasks.length,0);
assert.equal(stale.cockpitFresh,false);
assert.equal(view.records.find(r=>r.id==='job-result-scheduled-scheduled').state,'open');
const dated=structuredClone(snapshot);
dated.cockpit.events=[{id:'today',title:'Synthetic hearing',at:'2026-11-02',date_kind:'hearing',confirmed:true,observed_at:stamp,source:'Synthetic source'}];
const events=overview(dated,[],{balances:[],machines:[],integrated:[]},now,false).events;
assert.equal(events.length,1,'a date-only event today has no invented expired midnight');
assert.equal(events[0].dateOnly,true);
console.log('Cockpit state, coverage, execution-origin and unknown-date checks passed');

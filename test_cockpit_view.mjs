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
assert.equal(stale.coverageFresh,true,'a fifteen-minute publication remains valid as historical coverage');
assert.equal(stale.courtFresh,true,'court evidence keeps its original source age, separate from process liveness');
assert.equal(view.records.find(r=>r.id==='job-result-scheduled-scheduled').state,'open');
const dated=structuredClone(snapshot);
dated.cockpit.events=[{id:'today',title:'Synthetic hearing',at:'2026-11-02',date_kind:'hearing',confirmed:true,observed_at:stamp,source:'Synthetic source'}];
const events=overview(dated,[],{balances:[],machines:[],integrated:[]},now,false).events;
assert.equal(events.length,1,'a date-only event today has no invented expired midnight');
assert.equal(events[0].dateOnly,true);
dated.cockpit.events=[
 {id:'earlier',title:'Synthetic earlier',at:'2026-11-03T00:30:00+03:00',date_kind:'hearing',confirmed:true,observed_at:stamp,source:'Synthetic source'},
 {id:'later',title:'Synthetic later',at:'2026-11-02T22:00:00Z',date_kind:'hearing',confirmed:true,observed_at:stamp,source:'Synthetic source'}];
assert.deepEqual(overview(dated,[],{balances:[],machines:[],integrated:[]},now,false).events.map(e=>e.id),['court-earlier','court-later'],'different offsets sort by the actual event time');
const missingQuota=overview({observed_at_utc:stamp},[{account:{id:'no-quota',label:'Synthetic account'},view:{fresh:true,authorizationIssue:false,windows:[]}}],{balances:[],machines:[],integrated:[]},now,false);
assert.equal(missingQuota.records.some(r=>r.domain==='subscriptions'&&r.state==='unknown'),true,'missing windows are a coverage gap');
const resources={balances:[],machines:[],integrated:[{key:'synthetic',page:'subscriptions',title:'Synthetic integration',observed_at:stamp,current:true,tone:'warning',kind:'account',weekly_remaining:20,five_hour_remaining:80,problem:'Low quota'}]};
let integrated=reconcile(new Map(),overview({},[],resources,now,false).records);
const viewed=new Map([['integration-synthetic',integrated.get('integration-synthetic').revision]]);
resources.integrated[0].weekly_remaining=11;
integrated=reconcile(integrated,overview({},[],resources,now,false).records);
assert.equal(compact(integrated.get('integration-synthetic'),viewed),false,'integrated quota worsening re-escalates');
console.log('Cockpit state, coverage, execution-origin and unknown-date checks passed');

const renewal=structuredClone(snapshot);
renewal.mail_subscriptions={checked_at:stamp,coverage:[{mailbox:'test',status:'partial',checked_at:stamp,history_complete:false}],records:[{id:'a'.repeat(32),service:'example.test',amount:null,currency:null,amount_kind:'unknown',renewal_date:'2026-11-03',status:'observed',sources:[{mailbox:'test',ref:'b'.repeat(32),date:stamp,url:null,fields:['renewal']}]}]};
const renewalEvents=overview(renewal,[],{balances:[],machines:[],integrated:[]},now,false).events;
assert.equal(renewalEvents.length,1,'supported renewal dates join owner events without scanning mail');
assert.equal(renewalEvents[0].at,'2026-11-03');
assert.match(renewalEvents[0].detail,/Сумма продления неизвестна/);
assert.equal(renewalEvents[0].observedAt,stamp);

const reminders=structuredClone(snapshot),caseId='c'.repeat(32);
reminders.mail_secretary={checked_at:stamp,cases:[{id:caseId,service:'excalidraw',kind:'reply_needed',state:'needs_user',deadline:null,observed_at:stamp,updated_at:stamp,sources:['d'.repeat(32)]}]};
reminders.mail_control={available:true,decisions:{[caseId]:{action:'remind',status:'snoozed',request_id:'e'.repeat(32),at:stamp,remind_on:'2026-11-04'}}};
const ownerEvents=s=>overview(s,[],{balances:[],machines:[],integrated:[]},now,false).events;
assert.equal(ownerEvents(reminders).length,1,'a canonical reminder is an owner event');
assert.equal(ownerEvents(reminders)[0].at,'2026-11-04');
assert.equal(ownerEvents(reminders)[0].observedAt,stamp,'source age is not page-load time');
reminders.mail_control.decisions[caseId].status='cancelled';
assert.equal(ownerEvents(reminders).length,0,'verified reply cancellation removes the reminder');
Object.assign(reminders.mail_control.decisions[caseId],{status:'snoozed',request_id:'f'.repeat(32),remind_on:'2026-11-05'});
assert.equal(ownerEvents(reminders)[0].at,'2026-11-05','a newer reminder after a reply remains');
assert.equal(ownerEvents(reminders).length,1,'repeated snapshots do not accumulate events');
reminders.mail_control.queues={[caseId]:'done'};
assert.equal(ownerEvents(reminders).length,0,'a conflicting canonical queue does not revive a reminder');
delete reminders.mail_control.queues;reminders.mail_control.available=false;
assert.equal(ownerEvents(reminders).length,0,'an unavailable decision store does not confirm reminders');

const scheduled=structuredClone(snapshot);
Object.assign(scheduled.cockpit.tasks[0],{next_run_at:'2026-11-03T09:00:00Z',enabled:true});
assert.equal(ownerEvents(scheduled).length,0,'internal scheduled jobs stay out of owner dates');
assert.equal(overview(scheduled,[],{balances:[],machines:[],integrated:[]},now,false).tasks[0].next_run_at,'2026-11-03T09:00:00Z','the schedule remains available to Hermes details');
const beforeMidnight=Date.parse('2026-11-02T20:59:30Z'),midnight=structuredClone(snapshot);
midnight.cockpit.collected_at=new Date(beforeMidnight).toISOString();midnight.cockpit.events=[{id:'day',title:'Synthetic hearing',at:'2026-11-03',date_kind:'hearing',confirmed:true,observed_at:midnight.cockpit.collected_at,source:'Synthetic source'}];
assert.equal(overview(midnight,[],{balances:[],machines:[],integrated:[]},beforeMidnight,false).events[0].when,'Завтра');
assert.equal(overview(midnight,[],{balances:[],machines:[],integrated:[]},beforeMidnight+60000,false).events[0].when,'Сегодня');

const splitEvidence=structuredClone(renewal);
splitEvidence.mail_subscriptions.coverage.push({mailbox:'closed',status:'unavailable',checked_at:stamp,history_complete:false});
splitEvidence.mail_subscriptions.records[0].sources=[{mailbox:'closed',ref:'b'.repeat(32),date:stamp,url:null,fields:['renewal']},{mailbox:'test',ref:'c'.repeat(32),date:stamp,url:null,fields:['amount']}];
assert.equal(ownerEvents(splitEvidence).length,0,'an available amount source cannot confirm an unavailable renewal source');
const cancelled=structuredClone(renewal);cancelled.mail_subscriptions.records[0].status='cancelled';
assert.equal(ownerEvents(cancelled).length,0,'a cancellation is not an upcoming renewal');
assert.equal(overview(renewal,[],{balances:[],machines:[],integrated:[]},now,true).events.length,0,'transport failure cannot republish old dates as current');
const collision=structuredClone(renewal);
collision.cockpit.events=[{id:'renewal-'+ 'a'.repeat(32),title:'Distinct court event',at:'2026-11-03',date_kind:'hearing',confirmed:true,observed_at:stamp,source:'Court fixture'}];
assert.equal(new Set(ownerEvents(collision).map(e=>e.id)).size,2,'different source namespaces retain different evidence targets');

const boundaries=structuredClone(snapshot);
boundaries.cockpit.events=[
 {id:'last-calendar',title:'Last calendar day',at:'2026-11-09',date_kind:'confirmed_deadline',confirmed:true,observed_at:stamp,source:'Synthetic source'},
 {id:'too-late',title:'Outside calendar window',at:'2026-11-10',date_kind:'hearing',confirmed:true,observed_at:stamp,source:'Synthetic source'},
 {id:'past',title:'Past calendar day',at:'2026-11-01',date_kind:'hearing',confirmed:true,observed_at:stamp,source:'Synthetic source'},
 {id:'inferred',title:'Text mention',at:'2026-11-03',date_kind:'inferred',confirmed:false,observed_at:stamp,source:'Synthetic source'},
 {id:'unverified',title:'Unverified date',at:'2026-11-03',date_kind:'hearing',confirmed:false,observed_at:stamp,source:'Synthetic source'}];
assert.deepEqual(ownerEvents(boundaries).map(e=>[e.id,e.when]),[['court-last-calendar','Через 7 дн.']]);
const paid=structuredClone(renewal);Object.assign(paid.mail_subscriptions.records[0],{amount:'20.00',currency:'USD',amount_kind:'last_payment'});
paid.mail_subscriptions.records[0].sources[0].fields.push('amount');
assert.match(ownerEvents(paid)[0].detail,/Сумма продления неизвестна/,'an old payment is not the next renewal charge');
paid.mail_subscriptions.records[0].amount_kind='next_charge';
assert.match(ownerEvents(paid)[0].detail,/20.00 USD/);
paid.mail_subscriptions.coverage[0].checked_at='2026-10-01T00:00:00Z';
assert.equal(ownerEvents(paid).length,0,'a recent publication cannot freshen an old mailbox check');
console.log('Owner dates, canonical reminders, field-specific evidence and Istanbul boundaries passed');

const splitAmount=structuredClone(renewal);
Object.assign(splitAmount.mail_subscriptions.records[0],{amount:'99.00',currency:'USD',amount_kind:'next_charge'});
splitAmount.mail_subscriptions.coverage.push({mailbox:'closed',status:'unavailable',checked_at:stamp,history_complete:false});
splitAmount.mail_subscriptions.records[0].sources.push({mailbox:'closed',ref:'c'.repeat(32),date:stamp,url:null,fields:['amount']});
assert.match(ownerEvents(splitAmount)[0].detail,/Сумма продления неизвестна/,'an unavailable amount source cannot borrow fresh renewal evidence');
splitAmount.mail_subscriptions.coverage[1].status='ok';
assert.match(ownerEvents(splitAmount)[0].detail,/99.00 USD/);
assert.match(ownerEvents(splitAmount)[0].source,/cccccccc/,'the displayed charge keeps its own source reference');
splitAmount.mail_subscriptions.coverage[1].checked_at='2026-10-01T00:00:00Z';
assert.match(ownerEvents(splitAmount)[0].detail,/Сумма продления неизвестна/,'stale amount support stays unknown');

import {test,expect} from '@playwright/test';

test('Mac batteries show native 80 confirmation and no-connection without false zero',async({page},testInfo)=>{
 await page.goto('/');await page.locator('input[name=password]').fill('fixture-only-browser-password');await page.locator('button[type=submit]').click();
 const body=await (await page.request.get('/api/snapshot')).json();const stamp=new Date().toISOString();
 const source=body.operations.fleet.machines[0];source.kind='physical_mac';
 source.battery={status:'ok',observed_at:stamp,checked_at:stamp,charge_percent:100,health_percent:89,health_condition:'normal',cycle_count:210,is_charging:false,limit_status:'ok',limit_percent:80,limit_enabled:true};
 body.operations.fleet.machines.push({...source,id:'missing-mac',state:'not_enrolled',battery:{...source.battery,status:'not_connected',observed_at:null,charge_percent:null,health_percent:null,limit_percent:null,limit_enabled:null,cycle_count:null,is_charging:null,health_condition:'unknown',limit_status:'unavailable'}});
 body.operations.fleet.inventory_count=2;await page.route('**/api/refresh',r=>r.fulfill({json:body}));
 await page.locator('#refresh').click();await page.locator('#nav-machines').click();
 const good=page.locator('#machine-'+source.id),missing=page.locator('#machine-missing-mac');
 await expect(good).toContainText('Заряд: 100% · Здоровье: 89%');await expect(good).toContainText('Лимит 80% подтверждён');
 await expect(missing).toContainText('Нет связи с датчиком батареи · 80% не подтверждены');await expect(missing).toContainText('Заряд: неизвестен · Здоровье: неизвестно');
 await expect(good.locator('summary')).toBeVisible();await good.locator('summary').click();await expect(good).toContainText('Циклы: 210');
 await expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);await page.screenshot({path:testInfo.outputPath('mac-batteries.png'),fullPage:true});
 source.battery.limit_enabled=false;await page.locator('#refresh').click();await expect(good).toContainText('Лимит выключен · 80% не подтверждены');
 source.battery.observed_at=new Date(Date.now()-1801e3).toISOString();await page.locator('#refresh').click();await expect(good).toContainText('Данные батареи устарели · 80% не подтверждены');await expect(good).toContainText('Заряд: неизвестен');
});

test('machine aliases appear under one canonical card while unknown machines remain',async({page},testInfo)=>{
 await page.goto('/');await page.locator('input[name=password]').fill('fixture-only-browser-password');await page.locator('button[type=submit]').click();
 const body=await (await page.request.get('/api/snapshot')).json();
 const machine=body.operations.fleet.machines[0];machine.aliases=['old-node'];
 body.operations.fleet.machines.push({...machine,id:'unconfirmed-node',aliases:[],state:'not_enrolled',issues:[]});
 body.operations.fleet.inventory_count=2;
 await page.route('**/api/refresh',route=>route.fulfill({json:body}));
 await page.locator('#refresh').click();await page.locator('#nav-machines').click();
 await expect(page.locator('#machine-'+machine.id)).toContainText('Псевдонимы: old-node');
 await expect(page.locator('#machine-old-node')).toHaveCount(0);
 await expect(page.locator('#machine-unconfirmed-node')).toContainText('Диагностика не подключена');
 await expect(page.locator('#machine-count')).toContainText('2 записей');
 await expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
 await page.screenshot({path:testInfo.outputPath('machine-aliases.png'),fullPage:true});
});

test('password gate, four pages, quotas, unknown values and compact mobile layout',async({page},testInfo)=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 const unwanted=[];
 page.on('request',r=>{if(!r.url().startsWith('http://127.0.0.1:8877/')&&!r.url().startsWith('data:'))unwanted.push(r.url());});
 const denied=await page.request.get('/api/snapshot');expect(denied.status()).toBe(401);
 const writes=await page.request.post('/api/refresh');expect(writes.status()).toBe(405);
 await page.goto('/');await expect(page.locator('input[name=password]')).toBeVisible();
 await expect(page.locator('input[name=username]')).toHaveCount(0);
 await page.locator('input[name=password]').fill('fixture-only-browser-password');
 await page.locator('button[type=submit]').click();
 await expect(page.locator('#nav-overview')).toBeVisible();
 const cookies=await page.context().cookies();expect(cookies.find(c=>c.name==='__Host-cpa_session')?.expires-Date.now()/1000).toBeGreaterThan(29*86400);
 for(const route of ['overview','subscriptions','balances','machines']){
  await page.locator('#nav-'+route).click();await expect(page.locator('#page-'+route)).toBeVisible();
  await expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1)).toBe(true);
  if(route==='subscriptions'){
   await expect(page.locator('#accounts article').first()).toContainText('critical@example.test');
   await expect(page.locator('#accounts')).not.toContainText('disabled');
   await expect(page.locator('#authorization-accounts')).toContainText('authorization@example.test');
   await expect(page.locator('[data-account-id="critical"] .quota-critical')).toHaveCount(1);
   await expect(page.locator('[data-account-id="low"] .quota-low')).toHaveCount(1);
   await expect(page.locator('[data-account-id="unknown"]')).toContainText('Нет данных о квоте');
   await expect(page.locator('[data-account-id="unknown"] progress')).toHaveCount(1); // Only its measured 5h window.
  }
  if(route==='balances')await expect(page.locator('#balance-kie')).toContainText('Нет данных');
  await page.screenshot({path:testInfo.outputPath(route+'.png'),fullPage:true});
 }
 expect(errors).toEqual([]);expect(unwanted).toEqual([]);
});

test('cockpit keeps evidence, seen state, urgency, task origin and partial court coverage',async({page},testInfo)=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('/');await page.locator('input[name=password]').fill('fixture-only-browser-password');
 await page.locator('button[type=submit]').click();
 await expect(page.locator('#cockpit-decisions')).toContainText('critical@example.test');
 const low=page.locator('#cockpit-decisions .cockpit-row').filter({hasText:'low@example.test'}).first();
 await low.locator('a').click();
 await expect(page.locator('#page-evidence')).toBeVisible();
 await expect(page.locator('#evidence-content')).toContainText('20%');
 await page.locator('#evidence-back').click();
 await expect(page.locator('#cockpit-seen')).toHaveAttribute('open','');
 await expect.poll(()=>page.evaluate(()=>document.activeElement?.id?.startsWith('cockpit-row-'))).toBe(true);
 await expect(page.locator('#cockpit-decisions')).not.toContainText('low@example.test');
 await expect(page.locator('#cockpit-seen-count')).toContainText('Просмотрено');
 await page.reload();
 await expect(page.locator('#cockpit-decisions')).not.toContainText('low@example.test');
 const critical=page.locator('#cockpit-decisions .cockpit-row').filter({hasText:'critical@example.test'}).first();
 await critical.locator('a').click();await page.locator('#evidence-back').click();
 await expect(page.locator('#cockpit-decisions')).toContainText('critical@example.test');
 await page.locator('#nav-courts').click();
 await expect(page.locator('#court-summary')).toContainText('охват неполный');
 await expect(page.locator('#court-summary')).toContainText('Подтверждённый список недоступен');
 await page.locator('#nav-hermes').click();
 await expect(page.locator('#hermes-tasks')).toContainText('Плановый');
 await expect(page.locator('#hermes-tasks')).toContainText('Ручной');
 await expect(page.locator('#hermes-tasks')).toContainText('Выполнение не подтверждено');
 await page.locator('#nav-overview').click();
 await expect(page.locator('#page-overview')).toBeVisible();
 await expect(page.locator('#cockpit-active')).toContainText('Подтверждённых активных исполнений нет');
 await expect(page.locator('#cockpit-events')).not.toContainText('Заседание');
 await expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
 await page.screenshot({path:testInfo.outputPath('cockpit.png'),fullPage:true});
 expect(errors).toEqual([]);
});

test('changed, missing and recovered observations do not confuse seen with resolved',async({page})=>{
 await page.goto('/');await page.locator('input[name=password]').fill('fixture-only-browser-password');await page.locator('button[type=submit]').click();
 let body=await (await page.request.get('/api/snapshot')).json();
 await page.route('**/api/refresh',route=>route.fulfill({json:body}));
 const low=()=>page.locator('#cockpit-decisions .cockpit-row').filter({hasText:'low@example.test'}).first();
 await low().locator('a').click();await page.locator('#evidence-back').click();
 const account=body.accounts.find(a=>a.id==='low');
 account.quota.windows[0].remaining_percent=19;
 await page.reload();await page.locator('#refresh').click();
 await expect(low()).toContainText('19%');
 account.quota.observed_at=new Date(Date.now()-48*3600e3).toISOString();
 await page.locator('#refresh').click();
 await expect(low()).toHaveCount(0);
 await expect(page.locator('#cockpit-work')).toContainText('текущий статус неизвестен');
 account.quota.observed_at=new Date().toISOString();account.quota.windows[0].remaining_percent=80;
 await page.locator('#refresh').click();
 await expect(low()).toHaveCount(0);
 account.quota.windows[0].remaining_percent=19;
 await page.locator('#refresh').click();
 await expect(low()).toContainText('19%');
 const saved=await page.evaluate(()=>sessionStorage.getItem('cockpit-seen-v1'));
 expect(saved).not.toContain('example.test');expect(saved).not.toContain('quota-');
 expect(JSON.parse(saved).every(pair=>pair.every(v=>/^[a-f0-9]{16}$/.test(v)))).toBe(true);
 body.cockpit.tasks.find(t=>t.id==='unverified').liveness='verified';
 await page.locator('#refresh').click();await page.locator('#nav-hermes').click();
 const active=page.locator('#hermes-tasks .cockpit-row').filter({hasText:'Synthetic operations check'});
 await active.locator('a').click();await page.locator('#evidence-back').click();
 await expect(page.locator('#page-hermes')).toBeVisible();
 await expect.poll(()=>page.evaluate(()=>document.activeElement?.closest('#hermes-tasks')!==null)).toBe(true);
 const ids=await page.locator('[id]').evaluateAll(nodes=>nodes.map(n=>n.id));expect(new Set(ids).size).toBe(ids.length);
});

test('preparation remains visible after the source becomes healthy',async({page})=>{
 await page.goto('/');await page.locator('input[name=password]').fill('fixture-only-browser-password');await page.locator('button[type=submit]').click();
 const body=await(await page.request.get('/api/snapshot')).json(),stamp=new Date().toISOString(),m=body.operations.fleet.machines[0];
 m.state='observed_ok';m.issues=[];m.observed_at=stamp;
 body.cockpit.work={status:'ok',observed_at:stamp,items:[{record_id:'machine-'+m.id,condition_key:'disk:warning',fingerprint:'b'.repeat(64),source_state:'clear',source_at:stamp,queued_at:stamp,updated_at:stamp,state:'accepted',action:'prepare_fix',blocker:'none',decision:null,task_ref:null,execution_key:'b'.repeat(24),execution_state:'running',execution_liveness:'verified',actor:'infra-dev'}]};
 await page.route('**/api/refresh',r=>r.fulfill({json:body}));await page.locator('#refresh').click();
 await expect(page.locator('#cockpit-work')).toContainText(m.id);await expect(page.locator('#cockpit-work')).toContainText('Подготовка исправления');
 await expect(page.locator('#cockpit-work').getByRole('heading',{name:m.id,exact:true})).toBeVisible();
 await expect(page.locator('#cockpit-decisions')).not.toContainText(m.id);
 await page.locator('#nav-machines').click();await expect(page.locator('#machine-'+m.id)).toContainText('Без замечаний на замере');
 await expect(page.locator('#machine-'+m.id)).toContainText('Подготовка исправления');
 delete body.cockpit.work.items[0].actor;body.cockpit.work.items[0].action='inspect_disk';
 await page.locator('#refresh').click();await expect(page.locator('#machine-'+m.id)).toContainText('Анализ занятого места');
 await page.locator('#nav-overview').click();await expect(page.locator('#cockpit-work')).toContainText('Hermes · ops');
 body.cockpit.work.items[0].state='waiting';body.cockpit.work.items[0].action='test_fix';body.cockpit.work.items[0].blocker='no_safe_procedure';
 await page.locator('#refresh').click();await expect(page.locator('#cockpit-work')).toContainText('ops · ожидание');
 await expect(page.locator('#cockpit-work')).toContainText('Нужна проверенная процедура исправления');
 await expect(page.locator('#cockpit-decisions')).not.toContainText(m.id);
});

test('technical incidents belong to Hermes and only explicit owner requests become decisions',async({page},testInfo)=>{
 await page.goto('/');await page.locator('input[name=password]').fill('fixture-only-browser-password');await page.locator('button[type=submit]').click();
 let body=await(await page.request.get('/api/snapshot')).json();const stamp=new Date().toISOString();
 const m=body.operations.fleet.machines[0];m.state='degraded';m.issues=[{code:'service',text:'Тестовая служба требует диагностики',severity:'warning',observed_at:stamp,ttl_seconds:900}];
 const item={record_id:'machine-'+m.id,condition_key:'service:warning',fingerprint:'b'.repeat(64),source_state:'open',source_at:stamp,queued_at:stamp,updated_at:stamp,state:'queued',action:'diagnose',blocker:'none',decision:null,task_ref:null,execution_key:null,execution_state:'unknown',execution_liveness:'unverified'};
 body.cockpit.work.items.push(item);await page.route('**/api/refresh',r=>r.fulfill({json:body}));await page.locator('#refresh').click();
 await expect(page.locator('#cockpit-decisions')).not.toContainText(m.id);await expect(page.locator('#cockpit-work')).toContainText('Передано ops · ждёт разбора');
 item.state='accepted';item.execution_key='b'.repeat(24);item.execution_state='running';item.execution_liveness='verified';item.action='inspect_service';
 await page.locator('#refresh').click();await expect(page.locator('#cockpit-work')).toContainText('В работе · процесс подтверждён');
 item.actor='infra-dev';await page.locator('#refresh').click();await expect(page.locator('#cockpit-work')).toContainText('Hermes · infra-dev');await expect(page.locator('#cockpit-work')).toContainText('infra-dev · владелец на связи');
 item.execution_state='failed';item.execution_liveness='not_applicable';await page.locator('#refresh').click();await expect(page.locator('#cockpit-work')).toContainText('Запуск остановился без итога по проблеме');
 item.state='waiting';item.blocker='no_safe_procedure';await page.locator('#refresh').click();await expect(page.locator('#cockpit-work')).toContainText('Нужна проверенная процедура исправления');
 body.cockpit.work.observed_at=new Date(Date.now()-1801e3).toISOString();await page.locator('#refresh').click();
 await expect(page.locator('#cockpit-work')).toContainText('Последняя запись · текущее состояние не подтверждено');
 await expect(page.locator('#cockpit-work')).toContainText('Нужна проверенная процедура исправления');
 await expect(page.locator('#cockpit-work')).not.toContainText('владелец на связи');
 body.cockpit.work.observed_at=stamp;await page.locator('#refresh').click();
 await page.locator('#nav-machines').click();await expect(page.locator('#machine-'+m.id)).toContainText('Последний этап: Диагностика служб');await expect(page.locator('#machine-'+m.id)).not.toContainText('Что сделать:');
 await page.screenshot({path:testInfo.outputPath('incident-machine.png'),fullPage:true});await page.locator('#nav-overview').click();await expect(page.locator('#page-overview')).toBeVisible();await page.screenshot({path:testInfo.outputPath('incident-handoff.png'),fullPage:true});
 item.state='needs_user';item.blocker='owner_approval';item.decision='Разрешить тестовую процедуру с указанным окном?';await page.locator('#refresh').click();
 await expect(page.locator('#cockpit-decisions')).toContainText(m.id);await expect(page.locator('#cockpit-decisions')).toContainText(item.decision);
 m.issues[0].severity='critical';await page.locator('#refresh').click();await expect(page.locator('#cockpit-decisions')).not.toContainText(m.id);await expect(page.locator('#cockpit-work')).toContainText('Передача ещё не подтверждена');
 await expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
});

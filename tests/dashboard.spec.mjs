import {test,expect} from '@playwright/test';

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
 await expect(low()).toContainText('текущий статус неизвестен');
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

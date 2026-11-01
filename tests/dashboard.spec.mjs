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

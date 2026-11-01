import {defineConfig} from '@playwright/test';
export default defineConfig({
 testDir:'./tests', timeout:30000, workers:1, retries:0, reporter:'list',
 use:{baseURL:'http://127.0.0.1:8877',browserName:'chromium'},
 projects:[{name:'desktop',use:{viewport:{width:1440,height:1000}}},{name:'mobile',use:{viewport:{width:390,height:844},isMobile:true,hasTouch:true}}],
 webServer:{command:'python3 tools/preview.py',url:'http://127.0.0.1:8877',reuseExistingServer:false,timeout:20000}
});

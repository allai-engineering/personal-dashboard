import assert from 'node:assert/strict';
import {quotaTone} from './release/web/account-view.mjs';
for(const minutes of [300,10080]){
 for(const [remaining,tone] of [[0,'critical'],[9.99,'critical'],[10,'low'],[24.99,'low'],[25,''],[100,'']])assert.equal(quotaTone({state:'observed',window_minutes:minutes,remaining}),tone);
 for(const state of ['old','unknown'])assert.equal(quotaTone({state,window_minutes:minutes,remaining:5}),'');
}
for(const remaining of [null,undefined,NaN,-1,101,'5'])assert.equal(quotaTone({state:'observed',window_minutes:300,remaining}),'');
assert.equal(quotaTone({state:'observed',window_minutes:60,remaining:5}),'');
console.log('quota colors: strict 10/25 boundaries, five-hour/weekly, old and invalid values passed');

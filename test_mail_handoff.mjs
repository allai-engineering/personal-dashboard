import assert from 'node:assert/strict';
import {handoffLabel} from './release/web/mail-secretary.mjs';

assert.match(handoffLabel({status:'queued'}),/заявка сохранена/);
assert.match(handoffLabel({status:'dispatching'}),/Результат ещё не получен/);
assert.match(handoffLabel({status:'blocked',reason:'owner_login',diagnostic_completed:true}),/нужен ваш вход/);
assert.match(handoffLabel({status:'blocked',reason:'owner_login',diagnostic_completed:false}),/не подтверждено/);
assert.match(handoffLabel({status:'blocked',reason:'diagnostic_unavailable',diagnostic_completed:true}),/доступен не полностью/);

import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { findCloudAccount, inspectUserInfoResponse, normalizeExpiredFlag } from '../pages/index/account-validity.js';

assert.equal(normalizeExpiredFlag(true), true);
assert.equal(normalizeExpiredFlag('true'), true);
assert.equal(normalizeExpiredFlag('1'), true);
assert.equal(normalizeExpiredFlag(false), false);
assert.equal(normalizeExpiredFlag('false'), false);
assert.equal(normalizeExpiredFlag(0), false);

assert.equal(inspectUserInfoResponse({ statusCode: 401, data: {} }).state, 'expired');
assert.equal(inspectUserInfoResponse({ statusCode: 200, data: { success: false } }).state, 'expired');
assert.equal(inspectUserInfoResponse({ statusCode: 200, data: '<html>please login</html>' }).state, 'expired');
assert.equal(inspectUserInfoResponse({ statusCode: 200, data: '<html>gateway maintenance</html>' }).state, 'unknown');
assert.equal(inspectUserInfoResponse({ statusCode: 200, data: { success: true, data: { user_profile: { user_id: 8 } } } }).state, 'valid');
assert.equal(inspectUserInfoResponse({ networkError: true }).state, 'unknown');

const cloud = [{ phone: '13800000000', uid: 1 }, { phone: '13900000000', uid: 2 }];
assert.equal(findCloudAccount(cloud, { phone: '13900000000' }).uid, 2);
assert.equal(findCloudAccount(cloud, { uid: 1 }).phone, '13800000000');
assert.equal(findCloudAccount(cloud, { phone: '13700000000' }), undefined);

const indexSource = await readFile(new URL('../pages/index/index.vue', import.meta.url), 'utf8');
const deleteAccountBlock = indexSource.slice(
	indexSource.indexOf('const deleteAccount ='),
	indexSource.indexOf('// ================== 云端引擎与并发控制')
);
assert.match(deleteAccountBlock, /只会从当前手机移除此账号/);
assert.doesNotMatch(deleteAccountBlock, /queueCloudAccountDeletion|deleted_accounts/);
assert.doesNotMatch(indexSource, /deleted_accounts\s*:/, 'App 同步不能携带服务器删除墓碑');

console.log('account-validity: 18 assertions passed');

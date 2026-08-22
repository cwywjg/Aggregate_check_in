const AUTH_MESSAGE_PATTERN = /登录|登陆|失效|过期|认证|未授权|请重新|unauthori[sz]ed|forbidden|session|credential|token|login/i;
const LOGIN_PAGE_PATTERN = /<form[^>]+login|password|账号登录|扫码登录|passport|please\s+login|login/i;

export const normalizeExpiredFlag = value => {
	if (value === true || value === 1) return true;
	if (value === false || value === 0 || value === null || value === undefined || value === '') return false;
	return ['true', '1', 'expired', 'invalid'].includes(String(value).trim().toLowerCase());
};

// Only explicit authentication evidence changes an account to expired.
// WAF pages, gateway HTML and malformed transient responses stay unknown.
export const inspectUserInfoResponse = response => {
	if (!response || response.networkError || Number(response.statusCode) < 0) return { state: 'unknown', reason: 'network' };
	const statusCode = Number(response.statusCode || 0);
	if (statusCode === 401 || statusCode === 403) return { state: 'expired', reason: `http_${statusCode}` };
	if (statusCode < 200 || statusCode >= 300) return { state: 'unknown', reason: `http_${statusCode}` };
	const data = response.data;
	if (typeof data === 'string') {
		const isLoginPage = AUTH_MESSAGE_PATTERN.test(data) && LOGIN_PAGE_PATTERN.test(data);
		return { state: isLoginPage ? 'expired' : 'unknown', reason: isLoginPage ? 'login_page' : 'non_json_response' };
	}
	if (!data || typeof data !== 'object') return { state: 'unknown', reason: 'empty_response' };
	const profile = data?.data?.user_profile;
	if (data.success === true && profile && (profile.user_id || profile.uid || profile.nickname || profile.name)) {
		return { state: 'valid', reason: 'profile_ok', profile };
	}
	if ([401, 403, 1001, 1002].includes(Number(data.code))) return { state: 'expired', reason: `code_${data.code}` };
	const message = String(data.msg || data.message || data.detail || '');
	if (AUTH_MESSAGE_PATTERN.test(message)) return { state: 'expired', reason: 'auth_message' };
	if (data.success === false) return { state: 'expired', reason: 'success_false' };
	if (!profile) return { state: 'unknown', reason: 'no_profile' };
	return { state: 'unknown', reason: 'unrecognized_response' };
};

export const applyValidityResult = (account, result, checkedAt = Date.now()) => {
	const next = account;
	next.validityState = result?.state || 'unknown';
	next.validitySource = 'local';
	next.validityCheckedAt = checkedAt;
	if (next.validityState === 'valid') {
		next.expired = false;
		next.validityFailureCount = 0;
	} else if (next.validityState === 'expired') {
		next.expired = true;
		next.validityFailureCount = Number(next.validityFailureCount || 0) + 1;
	}
	return next;
};

export const findCloudAccount = (cloudAccounts, localAccount) => {
	const phone = String(localAccount?.phone || '');
	const uid = String(localAccount?.uid || '');
	return (Array.isArray(cloudAccounts) ? cloudAccounts : []).find(account => (
		phone && String(account?.phone || '') === phone
	) || (
		uid && String(account?.uid || account?.userId || '') === uid
	));
};

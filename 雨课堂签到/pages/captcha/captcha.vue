<template>
	<view class="captcha-page">
		<web-view
			:src="captchaHtmlPath"
			@message="onCaptchaMessage"
			@error="onWebviewError"
		></web-view>
	</view>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue';
import { onBackPress, onUnload } from '@dcloudio/uni-app';

const CAPTCHA_TIMEOUT_MS = 90000;
const captchaHtmlPath = ref(`/static/captcha.html?t=${Date.now()}`);
let settled = false;
let timeoutTimer = null;

const publishResult = payload => {
	if (settled) return;
	settled = true;
	setTimeout(() => {
		try {
			uni.$emit('captchaPageResult', payload);
		} catch (e) {
			console.warn('Failed to emit captcha result', e);
		}
	}, 30);
};

const returnToLogin = () => {
	setTimeout(() => {
		const pages = getCurrentPages();
		if (pages.length > 1) {
			uni.navigateBack({ delta: 1 });
		} else {
			uni.reLaunch({ url: '/pages/index/index' });
		}
	}, 80);
};

const cancelAndReturn = reason => {
	publishResult({ type: 'cancel', reason: reason || 'user_cancel' });
	returnToLogin();
};

const validCaptchaResult = result => (
	typeof result?.ticket === 'string' &&
	typeof result?.randstr === 'string' &&
	result.ticket.length >= 16 &&
	result.ticket.length <= 4096 &&
	result.randstr.length >= 4 &&
	result.randstr.length <= 256
);

const onCaptchaMessage = event => {
	if (settled) return;
	const messages = Array.isArray(event?.detail?.data)
		? event.detail.data
		: [event?.detail?.data].filter(Boolean);
	const result = [...messages].reverse().find(item => item && typeof item === 'object');
	if (!result) return;
	if (result.type === 'cancel' || result.action === 'cancel') {
		cancelAndReturn('html_cancel');
		return;
	}
	if (!validCaptchaResult(result)) return;
	publishResult({
		type: 'success',
		ticket: result.ticket,
		randstr: result.randstr
	});
	returnToLogin();
};

const onWebviewError = () => {
	if (settled) return;
	uni.showModal({
		title: '验证页面加载失败',
		content: '可以重新加载，也可以直接返回新增账号页面。',
		confirmText: '重新加载',
		cancelText: '返回',
		success: result => {
			if (result.confirm) {
				captchaHtmlPath.value = `/static/captcha.html?t=${Date.now()}`;
			} else {
				cancelAndReturn('webview_error');
			}
		}
	});
};

onMounted(() => {
	timeoutTimer = setTimeout(() => {
		if (settled) return;
		uni.showModal({
			title: '验证等待超时',
			content: '验证码长时间没有响应，已解除锁定并返回。请检查网络后重试。',
			showCancel: false,
			complete: () => cancelAndReturn('timeout')
		});
	}, CAPTCHA_TIMEOUT_MS);
});

onBackPress(() => {
	publishResult({ type: 'cancel', reason: 'system_back' });
	return false;
});

onUnload(() => {
	if (!settled) {
		publishResult({ type: 'cancel', reason: 'page_unload' });
	}
});

onUnmounted(() => {
	if (timeoutTimer) clearTimeout(timeoutTimer);
	timeoutTimer = null;
});
</script>

<style>
page,
.captcha-page {
	width: 100%;
	height: 100%;
	background: #F2F2F7;
}
</style>

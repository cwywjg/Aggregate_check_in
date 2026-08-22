<script>
	export default {
		onLaunch: function() {
			console.log('App Launch')
		},
		onShow: function() {
			console.log('App Show')
		},
		onHide: function() {
			console.log('App Hide')
		}
	}
</script>

<style>
	/* 全局页面公共 CSS：全面适配 Android 12/13/14/15 挖孔屏、手势栏、折叠屏及大字号缩放 */
	page {
		background-color: #F2F2F7;
		font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", Roboto, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
		-webkit-font-smoothing: antialiased;
		-moz-osx-font-smoothing: grayscale;
		-webkit-text-size-adjust: 100% !important;
		text-size-adjust: 100% !important;
		box-sizing: border-box;
		margin: 0;
		padding: 0;
		width: 100%;
		overflow-x: hidden;
	}

	*, *::before, *::after {
		box-sizing: border-box;
		-webkit-tap-highlight-color: transparent;
	}

	button {
		font-family: inherit;
	}

	input {
		font-family: inherit;
	}
</style>

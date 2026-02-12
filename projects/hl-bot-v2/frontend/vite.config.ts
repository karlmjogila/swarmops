import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [sveltekit()],
	server: {
		port: 5173,
		host: true,
		proxy: {
			'/api': {
				target: 'http://backend:8000',
				changeOrigin: true,
				rewrite: (path) => path.replace(/^\/api/, ''),
			},
			'/health': {
				target: 'http://backend:8000',
				changeOrigin: true,
			},
		},
	}
});

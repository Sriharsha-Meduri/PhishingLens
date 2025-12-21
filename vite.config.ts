import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react-swc';
import path from 'node:path';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const proxyPath = env.VITE_DEV_PROXY_PATH?.replace(/\/$/, '');
  const proxyTarget = env.VITE_API_BASE_URL?.replace(/\/$/, '');

  const proxy = proxyPath && proxyTarget
    ? {
        [proxyPath]: {
          target: proxyTarget,
          changeOrigin: true,
          secure: false,
          rewrite: (pathStr: string) => pathStr.replace(new RegExp(`^${proxyPath}`), '')
        }
      }
    : undefined;

  return {
    plugins: [react()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, 'src'),
        '@components': path.resolve(__dirname, 'src/components'),
        '@pages': path.resolve(__dirname, 'src/pages'),
        '@hooks': path.resolve(__dirname, 'src/hooks'),
        '@utils': path.resolve(__dirname, 'src/utils'),
        '@styles': path.resolve(__dirname, 'src/styles')
      }
    },
    server: {
      port: 5173,
      proxy
    }
  };
});

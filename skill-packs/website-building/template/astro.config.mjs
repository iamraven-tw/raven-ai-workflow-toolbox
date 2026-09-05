// Astro 靜態站點設定。site 與 theme 由 site.config.mjs 提供。
// @theme 別名指向目前選定的主題目錄，切換主題只要改 site.config.mjs 的 theme 再重建。
import { defineConfig } from 'astro/config';
import { fileURLToPath } from 'node:url';
import tailwindcss from '@tailwindcss/vite';
import sitemap from '@astrojs/sitemap';
import { site } from './site.config.mjs';

const themeDir = fileURLToPath(new URL(`./src/themes/${site.theme}/`, import.meta.url));

export default defineConfig({
  site: site.url,
  output: 'static',
  trailingSlash: 'ignore',
  integrations: [sitemap()],
  vite: {
    plugins: [tailwindcss()],
    resolve: {
      alias: { '@theme': themeDir },
    },
  },
});

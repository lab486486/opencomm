// @ts-check
import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';
import { showAdminApi } from './admin-api.mjs';

export default defineConfig({
  site: 'https://opencomm.net',
  trailingSlash: 'always',
  integrations: [
    showAdminApi(),
    sitemap({
      filter: (page) => !page.includes('/admin') && !page.includes('/p/'),
    }),
  ],
});

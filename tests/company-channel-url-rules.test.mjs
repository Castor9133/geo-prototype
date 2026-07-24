import assert from 'node:assert/strict';
import {access, readFile} from 'node:fs/promises';
import path from 'node:path';
import test from 'node:test';
import {fileURLToPath} from 'node:url';

const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const read = (relative) => readFile(path.join(projectRoot, relative), 'utf8');

test('retired company product URLs permanently redirect to GEO Suite', async () => {
  const [companyPages, retiredPages, nginx, runtime, header, navigation] = await Promise.all([
    read('backend/app/web/company_pages.py'),
    read('backend/app/web/retired_pages.py'),
    read('infra/nginx/default.conf'),
    read('dist/js/common.js'),
    read('dist/components/header.html'),
    read('backend/app/services/navigation_settings.py'),
  ]);

  assert.match(companyPages, /SUITE_REDIRECT = "\/suite"/);
  assert.match(companyPages, /@router\.get\("\/companies"\)/);
  assert.match(companyPages, /status_code=301/);
  assert.match(retiredPages, /@router\.get\("\/company\.html"\)/);

  assert.match(nginx, /location @default_homepage \{\s*return 302 \/suite;/);
  assert.match(nginx, /location = \/companies \{\s*return 301 \/suite;/);
  assert.match(nginx, /location = \/company \{\s*return 301 \/suite;/);
  assert.match(nginx, /location = \/submit-company \{\s*return 301 \/suite;/);
  assert.match(nginx, /location \^~ \/c\/ \{\s*return 301 \/suite;/);

  assert.doesNotMatch(runtime, /nav\.companies/);
  assert.doesNotMatch(header, /nav\.companies/);
  assert.doesNotMatch(header, /href="\/companies"/);
  assert.match(navigation, /REMOVED_NAVIGATION_IDS = frozenset\(\{"companies", "experts", "tutorial", "github"\}\)/);
  assert.doesNotMatch(navigation, /\{"id": "companies"/);
});

test('company product static assets are deleted', async () => {
  for (const relative of [
    'dist/company.html',
    'dist/company-submit.html',
    'dist/js/company.js',
    'dist/js/submit-company.js',
    'dist/js/company-submit-page.js',
    'dist/css/company.css',
    'dist/admin/companies.html',
    'apps/web/app/[locale]/companies/page.tsx',
    'apps/admin/app/[locale]/companies/page.tsx',
  ]) {
    await assert.rejects(() => access(path.join(projectRoot, relative)), {code: 'ENOENT'}, relative);
  }
});

test('homepage no longer ships the company directory hero', async () => {
  const homepage = await read('dist/index.html');
  assert.doesNotMatch(homepage, /今日公司推荐/);
  assert.doesNotMatch(homepage, /热门公司/);
  assert.doesNotMatch(homepage, /data-submit-company-trigger/);
  assert.doesNotMatch(homepage, /submit-company\.js/);
  assert.match(homepage, /GEOrank 工作台/);
  assert.match(homepage, /href="\/suite"/);
});

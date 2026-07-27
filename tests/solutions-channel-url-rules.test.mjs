import assert from 'node:assert/strict';
import {access, readFile} from 'node:fs/promises';
import path from 'node:path';
import test from 'node:test';
import {fileURLToPath} from 'node:url';

const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const read = (relative) => readFile(path.join(projectRoot, relative), 'utf8');

test('retired solutions and plans product URLs permanently redirect to GEO Suite', async () => {
  const [solutionPages, nginx, runtime, header, navigation, workflow] = await Promise.all([
    read('backend/app/web/solution_pages.py'),
    read('infra/nginx/default.conf'),
    read('dist/js/common.js'),
    read('dist/components/header.html'),
    read('backend/app/services/navigation_settings.py'),
    read('dist/js/suite-workflow.js'),
  ]);

  assert.match(solutionPages, /SUITE_REDIRECT = "\/suite"/);
  assert.match(solutionPages, /@router\.get\("\/solutions"\)/);
  assert.match(solutionPages, /@router\.get\("\/plans"\)/);
  assert.match(solutionPages, /status_code=301/);

  assert.match(nginx, /location = \/solutions \{\s*return 301 \/suite;/);
  assert.match(nginx, /location = \/plans \{\s*return 301 \/suite;/);
  assert.match(nginx, /location = \/qa \{\s*return 301 \/suite;/);
  assert.match(nginx, /location \^~ \/solutions\/ \{\s*return 301 \/suite;/);
  assert.match(nginx, /location = \/admin\/solutions \{ return 301 \/admin\/;/);

  assert.doesNotMatch(runtime, /nav\.solutions/);
  assert.doesNotMatch(runtime, /nav\.plans/);
  assert.doesNotMatch(header, /nav\.solutions/);
  assert.doesNotMatch(header, /nav\.plans/);
  assert.doesNotMatch(header, /href="\/solutions"/);
  assert.doesNotMatch(header, /href="\/plans"/);
  assert.match(
    navigation,
    /REMOVED_NAVIGATION_IDS = frozenset\(\{"companies", "experts", "tutorial", "github", "solutions", "plans"\}\)/
  );
  assert.doesNotMatch(navigation, /\{"id": "solutions"/);
  assert.doesNotMatch(navigation, /\{"id": "plans"/);

  assert.match(workflow, /next: 'keywords'/);
  assert.doesNotMatch(workflow, /id: 'solutions'/);
  assert.doesNotMatch(workflow, /href: '\/solutions'/);
  assert.doesNotMatch(workflow, /href: '\/plans'/);
});

test('solutions and plans product static assets are deleted', async () => {
  for (const relative of [
    'dist/solutions.html',
    'dist/plans.html',
    'dist/js/solutions.js',
    'dist/js/plans.js',
    'dist/css/solutions.css',
    'dist/css/plans.css',
    'dist/admin/solutions.html',
    'apps/web/app/[locale]/solutions/page.tsx',
    'apps/web/app/[locale]/plans/page.tsx',
    'apps/admin/app/[locale]/solutions/page.tsx',
  ]) {
    await assert.rejects(() => access(path.join(projectRoot, relative)), {code: 'ENOENT'}, relative);
  }
});

test('suite workflow order is diagnostic then keywords without solutions', async () => {
  const workflow = await read('dist/js/suite-workflow.js');
  const ids = [...workflow.matchAll(/id:\s*'([^']+)'/g)].map((match) => match[1]);
  const stepIds = ids.filter((id) =>
    ['diagnostic', 'keywords', 'handoff', 'review', 'knowledge', 'trust_asset', 'measure', 'solutions', 'plans'].includes(id)
  );
  assert.deepEqual(stepIds.slice(0, 7), [
    'diagnostic',
    'keywords',
    'handoff',
    'review',
    'knowledge',
    'trust_asset',
    'measure',
  ]);
  assert.ok(!stepIds.includes('solutions'));
  assert.ok(!stepIds.includes('plans'));
});

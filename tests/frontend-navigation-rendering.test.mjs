import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import path from 'node:path';
import test from 'node:test';
import {fileURLToPath} from 'node:url';

const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const frontendHtmlDir = path.join(projectRoot, 'dist');
const sharedFrontendScriptPath = path.join(projectRoot, 'dist', 'js', 'common.js');
const sharedFrontendCssPath = path.join(projectRoot, 'dist', 'css', 'common.css');
const sharedHeaderPath = path.join(projectRoot, 'dist', 'components', 'header.html');
const companiesDocumentPath = path.join(projectRoot, 'dist', 'index.html');
const sharedTailwindPath = path.join(projectRoot, 'dist', 'css', 'public-tailwind.css');
const navigationPaintAssetVersion = '20260724-demo-no-auth';
const moduleControllerAssetVersion = navigationPaintAssetVersion;
const publicStaticFrontendFiles = [
  'diagnostic.html',
  'index.html',
  'keywords.html',
  'login.html',
  'profile.html',
  'register.html',
  'tools.html'
];
const moduleControllerPaths = [
  'diagnostic.js',
  'index.js',
  'keywords.js',
  'tools.js'
].map((file) => path.join(projectRoot, 'dist', 'js', file));
const serverRenderedFrontendPaths = [];
const removedProductFrontendFiles = [
  'experts.html',
  'tutorial.html',
  'company.html',
  'company-submit.html',
  'solutions.html',
  'plans.html',
  'js/experts.js',
  'js/tutorial.js',
  'js/company.js',
  'js/submit-company.js',
  'js/company-submit-page.js',
  'js/solutions.js',
  'js/plans.js',
  'css/experts.css',
  'css/tutorial.css',
  'css/company.css',
  'css/solutions.css',
  'css/plans.css',
  'admin/experts.html',
  'admin/tutorials.html',
  'admin/tutorials-edit.html',
  'admin/companies.html',
  'admin/solutions.html'
];

test('removed product modules no longer ship static frontend assets', async () => {
  const {access} = await import('node:fs/promises');
  for (const relative of removedProductFrontendFiles) {
    await assert.rejects(
      () => access(path.join(frontendHtmlDir, relative)),
      {code: 'ENOENT'},
      relative
    );
  }
});

test('every static frontend page paints without a whole-document opacity gate', async () => {
  const htmlFiles = publicStaticFrontendFiles;

  assert.equal(htmlFiles.length, 7);
  for (const file of htmlFiles) {
    const html = await readFile(path.join(frontendHtmlDir, file), 'utf8');
    assert.doesNotMatch(
      html,
      /(?:\bbody\s*\{[^}]*\bopacity\s*:\s*0(?:\.0+)?|<body\b[^>]*\bstyle=["'][^"']*\bopacity\s*:\s*0(?:\.0+)?)/is,
      file
    );
  }
});

test('server-rendered frontend templates paint without a whole-document opacity gate', async () => {
  for (const templatePath of serverRenderedFrontendPaths) {
    const source = await readFile(templatePath, 'utf8');
    assert.doesNotMatch(
      source,
      /body\{\{opacity:0(?:\.0+)?|document\.body\.style\.(?:opacity|transition)\s*=/,
      path.relative(projectRoot, templatePath)
    );
  }
});

test('all frontend documents request cache-busted shared shell assets', async () => {
  const htmlFiles = publicStaticFrontendFiles;
  const documentPaths = [
    ...htmlFiles.map((file) => path.join(frontendHtmlDir, file)),
    ...serverRenderedFrontendPaths
  ];

  for (const documentPath of documentPaths) {
    const source = await readFile(documentPath, 'utf8');
    assert.match(
      source,
      /\/css\/common\.css\?v=[^"'\s>]+/,
      `${path.relative(projectRoot, documentPath)} common.css`
    );
    assert.match(
      source,
      /\/js\/common\.js\?v=[^"'\s>]+/,
      `${path.relative(projectRoot, documentPath)} common.js`
    );
  }
});

test('Tailwind runtime dependencies do not block body parsing', async () => {
  const htmlFiles = publicStaticFrontendFiles;
  const documentPaths = [
    ...htmlFiles.map((file) => path.join(frontendHtmlDir, file)),
    ...serverRenderedFrontendPaths
  ];

  for (const documentPath of documentPaths) {
    const source = await readFile(documentPath, 'utf8');
    const tailwindScripts = [...source.matchAll(/<script\b[^>]*\bsrc=["'][^"']*tailwind[^"']*["'][^>]*>/gi)];
    for (const [tag] of tailwindScripts) {
      assert.match(tag, /\bdefer\b/i, `${path.relative(projectRoot, documentPath)}: ${tag}`);
    }
  }
});

test('frontend documents ship Tailwind styles locally before first paint', async () => {
  const htmlFiles = publicStaticFrontendFiles;
  const documentPaths = [
    ...htmlFiles.map((file) => path.join(frontendHtmlDir, file)),
    ...serverRenderedFrontendPaths
  ];
  const css = await readFile(sharedTailwindPath, 'utf8');

  assert.match(css, /\.bg-primary\{/);
  assert.match(css, /\.md\\:flex\{/);
  assert.match(css, /\.max-w-5xl\{/);

  for (const documentPath of documentPaths) {
    const source = await readFile(documentPath, 'utf8');
    assert.doesNotMatch(
      source,
      /cdn\.tailwindcss\.com|\/js\/tailwind\.config\.js/,
      path.relative(projectRoot, documentPath)
    );
    if (documentPath === companiesDocumentPath) {
      assert.match(source, /\/css\/index-tailwind\.css\?v=20260716-first-paint/);
      continue;
    }
    assert.match(
      source,
      /\/css\/public-tailwind\.css\?v=20260716-first-paint-lifecycle/,
      path.relative(projectRoot, documentPath)
    );
  }
});

test('module controller documents request a cache-busted lifecycle asset', async () => {
  const htmlFiles = publicStaticFrontendFiles;
  const documentPaths = [
    ...htmlFiles.map((file) => path.join(frontendHtmlDir, file)),
    ...serverRenderedFrontendPaths
  ];
  const controllerNames = moduleControllerPaths.map((file) => path.basename(file, '.js'));
  const controllerPattern = new RegExp(
    `<script\\b[^>]*\\bsrc=["']/js/(?:${controllerNames.join('|')})\\.js\\?v=([^"']+)["'][^>]*>`,
    'g'
  );

  const referencedControllers = new Set();
  for (const documentPath of documentPaths) {
    const source = await readFile(documentPath, 'utf8');
    for (const match of source.matchAll(controllerPattern)) {
      assert.ok(match[1], `${path.relative(projectRoot, documentPath)}: ${match[0]}`);
      const fileName = match[0].match(/\/js\/([^"?]+)\.js/)?.[1];
      if (fileName) referencedControllers.add(`${fileName}.js`);
    }
  }
  assert.ok(referencedControllers.has('index.js'));
  assert.ok(referencedControllers.has('diagnostic.js'));
});

test('the shared frontend shell mounts before asynchronous configuration hydration', async () => {
  const source = await readFile(sharedFrontendScriptPath, 'utf8');
  const mountCall = source.indexOf('ComponentLoader.mountFallbacks();');
  const domReadyListener = source.lastIndexOf("document.addEventListener('DOMContentLoaded'");

  assert.ok(mountCall >= 0, 'expected the inline header/footer shell to mount synchronously');
  assert.ok(mountCall < domReadyListener, 'expected the inline shell before DOMContentLoaded hydration');
  assert.doesNotMatch(source, /document\.body\.style\.(?:opacity|transition)\s*=/);
  assert.doesNotMatch(source, /document\.addEventListener\('DOMContentLoaded',\s*async/);
  assert.match(source, /void Promise\.allSettled\(shellLoads\)/);
  assert.doesNotMatch(source, /Promise\.all\([^)]*ModuleGate\.load/);
  assert.match(
    source,
    /void PageLifecycle\.run\(\(\) => \{[\s\S]*?Voting\.init\(\);[\s\S]*?Search\.init\(\);[\s\S]*?\}\);/
  );
});

test('new frontend JavaScript reveals a legacy cached transparent document before hydration', async () => {
  const source = await readFile(sharedFrontendScriptPath, 'utf8');
  const revealCall = source.indexOf('ComponentLoader.revealLegacyDocument();');
  const domReadyListener = source.lastIndexOf("document.addEventListener('DOMContentLoaded'");

  assert.ok(revealCall >= 0, 'expected a JavaScript compatibility reveal for cached HTML and CSS');
  assert.ok(revealCall < domReadyListener, 'expected the compatibility reveal before async hydration');
  assert.match(
    source,
    /revealLegacyDocument\(\)\s*\{[\s\S]*?getComputedStyle\(body\)\.opacity[\s\S]*?body\.style\.opacity\s*=\s*'1'[\s\S]*?body\.style\.transition\s*=\s*'none'/
  );
});

test('the immediate header is complete before asynchronous configuration loads', async () => {
  const [source, header] = await Promise.all([
    readFile(sharedFrontendScriptPath, 'utf8'),
    readFile(sharedHeaderPath, 'utf8')
  ]);
  const inlineHeader = source.match(/const HEADER_HTML = `([\s\S]*?)`;/)?.[1] || '';

  assert.ok(inlineHeader, 'expected a complete immediate header');
  assert.match(inlineHeader, /<nav\b[^>]*id="main-nav"/);
  assert.match(inlineHeader, /data-nav-link/);
  assert.match(inlineHeader, /data-auth-trigger/);
  assert.match(inlineHeader, /id="mobile-menu-toggle"/);
  assert.doesNotMatch(inlineHeader, /data-navigation-item="github"/);
  assert.doesNotMatch(inlineHeader, /href="\/experts"/);
  assert.doesNotMatch(inlineHeader, /href="\/tutorial"/);
  assert.doesNotMatch(inlineHeader, /href="\/companies"/);
  assert.doesNotMatch(inlineHeader, /href="\/solutions"/);
  assert.doesNotMatch(inlineHeader, /href="\/plans"/);
  assert.doesNotMatch(inlineHeader, /nav\.companies/);
  assert.doesNotMatch(inlineHeader, /nav\.solutions/);
  assert.doesNotMatch(inlineHeader, /nav\.plans/);
  assert.doesNotMatch(header, /data-navigation-item="github"/);
  assert.doesNotMatch(header, /href="\/experts"/);
  assert.doesNotMatch(header, /href="\/tutorial"/);
  assert.doesNotMatch(header, /href="\/companies"/);
  assert.doesNotMatch(header, /href="\/solutions"/);
  assert.doesNotMatch(header, /href="\/plans"/);
  assert.doesNotMatch(header, /nav\.companies/);
  assert.doesNotMatch(header, /nav\.solutions/);
  assert.doesNotMatch(header, /nav\.plans/);
  assert.doesNotMatch(source, /HEADER_SHELL_HTML/);
  assert.match(
    source,
    /mountFallbacks\(\)\s*\{[\s\S]*?header\.innerHTML\s*=\s*HEADER_HTML/
  );
  assert.match(
    source,
    /loadHeader\(\)\s*\{[\s\S]*?header\?\.querySelector\('#main-nav'\)[\s\S]*?this\.load\('\/components\/header\.html'/
  );
});

test('first-frame header controls render without external icon fonts', async () => {
  const [source, sharedHeader] = await Promise.all([
    readFile(sharedFrontendScriptPath, 'utf8'),
    readFile(sharedHeaderPath, 'utf8')
  ]);
  const inlineHeader = source.match(/const HEADER_HTML = `([\s\S]*?)`;/)?.[1] || '';

  for (const [label, header] of [
    ['inline header', inlineHeader],
    ['shared header', sharedHeader]
  ]) {
    assert.equal([...header.matchAll(/<svg\b/g)].length, 2, label);
    assert.doesNotMatch(
      header,
      /class="material-symbols-outlined[^>]*">\s*(?:person|menu)\s*</,
      label
    );
  }
});

test('module configuration updates the visible header independently of component hydration', async () => {
  const source = await readFile(sharedFrontendScriptPath, 'utf8');

  assert.match(
    source,
    /whenAvailable\(\)\s*\{[\s\S]*?ModuleGate\.load\(\)[\s\S]*?ModuleGate\.applyHeader\(\);[\s\S]*?ModuleGate\.guardCurrentPage\(\)/
  );
});

test('the fetched header becomes interactive before module configuration resolves', async () => {
  const source = await readFile(sharedFrontendScriptPath, 'utf8');
  const loadHeader = source.match(/async loadHeader\(\)\s*\{([\s\S]*?)\n\s*\},/)?.[1] || '';

  assert.ok(loadHeader, 'expected the shared header hydration method');
  assert.ok(
    loadHeader.indexOf('Navigation.init();') < loadHeader.indexOf('await ModuleGate.load();'),
    'expected navigation binding before the module configuration request'
  );
});

test('module page controllers wait for the shared availability contract', async () => {
  const commonSource = await readFile(sharedFrontendScriptPath, 'utf8');

  assert.match(commonSource, /const PageLifecycle\s*=\s*\{/);
  assert.match(commonSource, /run\(callback\)\s*\{[\s\S]*?whenAvailable\(\)/);
  assert.match(commonSource, /new CustomEvent\('georank:page-available'/);

  for (const controllerPath of moduleControllerPaths) {
    const source = await readFile(controllerPath, 'utf8');
    assert.match(
      source,
      /PageLifecycle\?\.run\?\.bind\([^)]+\)\s*\|\|\s*\(\(callback\)\s*=>\s*callback\(\)\)/,
      path.relative(projectRoot, controllerPath)
    );
    assert.doesNotMatch(source, /DOMContentLoaded/, path.relative(projectRoot, controllerPath));
  }
});

test('shared hydration can start before deferred third-party scripts finish', async () => {
  const source = await readFile(sharedFrontendScriptPath, 'utf8');

  assert.match(
    source,
    /whenDomReady\(\)\s*\{[\s\S]*?document\.body\s*&&\s*document\.querySelector\('main'\)[\s\S]*?Promise\.resolve\(\)/
  );
  assert.match(source, /function initializeFrontend\(\)/);
  assert.match(
    source,
    /if \(document\.body\)\s*\{[\s\S]*?initializeFrontend\(\);[\s\S]*?\}\s*else\s*\{[\s\S]*?DOMContentLoaded/
  );
});

test('the profile controller can initialize before deferred Tailwind completes', async () => {
  const [source, html] = await Promise.all([
    readFile(path.join(projectRoot, 'dist', 'js', 'profile.js'), 'utf8'),
    readFile(path.join(projectRoot, 'dist', 'profile.html'), 'utf8')
  ]);

  assert.match(source, /async function initProfile\(\)/);
  assert.match(html, /\/js\/profile\.js\?v=20260716-first-paint-lifecycle/);
  assert.match(
    source,
    /if \(document\.body\)\s*\{[\s\S]*?void initProfile\(\);[\s\S]*?\}\s*else\s*\{[\s\S]*?DOMContentLoaded/
  );
});

test('component hydration has a bounded fallback and reports failures', async () => {
  const source = await readFile(sharedFrontendScriptPath, 'utf8');

  assert.match(source, /const COMPONENT_LOAD_TIMEOUT_MS\s*=\s*2500/);
  assert.match(
    source,
    /async load\([^)]*\)\s*\{[\s\S]*?new AbortController\(\)[\s\S]*?controller\.abort\(\)[\s\S]*?fetch\(url,\s*\{[\s\S]*?signal:\s*controller\.signal/
  );
  assert.match(source, /console\.warn\('\[GEOrank\] component load failed; using fallback'/);
  assert.match(source, /window\.clearTimeout\(timeout\)/);
});

test('shell hydration reports downstream initialization failures', async () => {
  const source = await readFile(sharedFrontendScriptPath, 'utf8');

  assert.match(
    source,
    /Promise\.allSettled\(shellLoads\)\.then\(results => \{[\s\S]*?result\.status !== 'rejected'[\s\S]*?console\.warn\('\[GEOrank\] shell hydration failed'/
  );
});

test('the inline and fetched headers share the signed-out authentication destination', async () => {
  const [source, header] = await Promise.all([
    readFile(sharedFrontendScriptPath, 'utf8'),
    readFile(sharedHeaderPath, 'utf8')
  ]);
  const inlineHeader = source.match(/const HEADER_HTML = `([\s\S]*?)`;/)?.[1] || '';
  const navigationContract = (html) => [...html.matchAll(
    /<a\s+href="([^"]+)"\s+data-nav-link\s+data-i18n="([^"]+)"/g
  )].map((match) => `${match[2]}:${match[1]}`);

  assert.ok(inlineHeader, 'expected the full offline header fallback');
  assert.deepEqual(navigationContract(inlineHeader), navigationContract(header));
  assert.match(inlineHeader, /href="\/login"\s+data-auth-trigger\s+data-profile-link/);
  assert.match(header, /href="\/login"[\s\S]{0,120}data-auth-trigger[\s\S]{0,120}data-profile-link/);
  assert.match(inlineHeader, /id="mobile-menu-toggle"/);
  assert.match(header, /id="mobile-menu-toggle"/);
});

test('shared frontend styles keep legacy cached documents visible without disabling body transitions globally', async () => {
  const css = await readFile(sharedFrontendCssPath, 'utf8');

  assert.match(css, /html\s+body\s*\{[^}]*opacity:\s*1\s*!important/s);
  assert.doesNotMatch(css, /html\s+body\s*\{[^}]*transition:\s*none\s*!important/s);
});

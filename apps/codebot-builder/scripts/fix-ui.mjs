import fs from 'fs';

function read(p){ return fs.existsSync(p) ? fs.readFileSync(p,'utf8') : null; }
function write(p,s){ fs.writeFileSync(p,s,{encoding:'utf8'}); }

function appendGlobalsScaffold() {
  const p = 'app/globals.css';
  const s0 = read(p);
  if (s0.includes('/* CodeBot UI scaffold */')) return;

  const scaffold =
'\n\n/* CodeBot UI scaffold */\n' +
':root{\n' +
'  --cb-maxw: 1200px;\n' +
'}\n\n' +
'.cb-container{\n' +
'  max-width: var(--cb-maxw);\n' +
'  margin: 0 auto;\n' +
'  padding: 20px 24px;\n' +
'}\n\n' +
'.cb-card{\n' +
'  border: 1px solid rgba(255,255,255,0.08);\n' +
'  background: rgba(0,0,0,0.25);\n' +
'  border-radius: 14px;\n' +
'  padding: 16px;\n' +
'  backdrop-filter: blur(8px);\n' +
'}\n\n' +
'.cb-h1{ font-size: 22px; font-weight: 700; line-height: 1.2; }\n' +
'.cb-sub{ opacity: 0.8; margin-top: 4px; }\n' +
'.cb-row{ display: flex; gap: 10px; flex-wrap: wrap; align-items: center; }\n' +
'.cb-spacer{ height: 12px; }\n\n' +
'.cb-grid-2{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }\n' +
'@media (max-width: 980px){ .cb-grid-2{ grid-template-columns: 1fr; } }\n\n' +
'.cb-pre{\n' +
'  white-space: pre-wrap;\n' +
'  word-break: break-word;\n' +
'  opacity: 0.85;\n' +
'  font-size: 13px;\n' +
'  line-height: 1.45;\n' +
'}\n';

  write(p, s0 + scaffold);
}

function injectUIDebugFlag(filePath) {
  const s0 = read(filePath);

  let s = s0;

    s = s.replace(
      /export default function ([A-Za-z0-9_]+)\(\)\s*\{/,
      (m, name) => 'export default function ' + name + '() {\n  const UI_DEBUG = process.env.NEXT_PUBLIC_UI_DEBUG === "1";'
    );
  }

  write(filePath, s);
}

function ensureContainerWrapper(filePath) {
  const s0 = read(filePath);

  let s = s0;
  if (s.includes('cb-container')) return;

  // Add cb-container to the first returned div className if possible
  const re = /return\s*\(\s*\n\s*<div([^>]*)className=\{?['"]([^'"]*)['"]\}?/m;
  if (re.test(s)) {
    s = s.replace(re, (m, pre, cls) => {
      if (cls.includes('cb-container')) return m;
      return 'return (\n    <div' + pre + 'className="' + cls + ' cb-container"';
    });
    write(filePath, s);
    return;
  }

  // Fallback: wrap entire return content
  if (s.includes('return (')) {
    s = s.replace(/return\s*\(\s*\n\s*</m, 'return (\n    <div className="cb-container">\n      <');
    s = s.replace(/\n\);\s*$/m, '\n    </div>\n  );\n');
  }

  write(filePath, s);
}

function stripBigDebugBlocks(filePath) {
  // Minimal safety: remove obvious debug paragraphs if present
  const s0 = read(filePath);

  let s = s0;

  // If already gated, do nothing
  if (s.includes('{UI_DEBUG &&')) return;

  // Replace a few known “wall of text” markers by gating them (best-effort, non-AST)
  const markers = [
    'No guessing, no drift',
    'Verified via curl',
    'Live endpoints',
    'If "Upgrade" fails',
    'Behavior goal:',
    'Session auth',
    'Cookie path='
  ];

  const lines = s.split('\n');
  const out = [];
  for (const line of lines) {
    if (markers.some(m => line.includes(m))) {
      out.push('{UI_DEBUG && (');
      out.push('<div className="cb-card"><div className="cb-pre">');
      out.push(line);
      out.push('</div></div>');
      out.push(')}');
    } else {
      out.push(line);
    }
  }
  write(filePath, out.join('\n'));
}

appendGlobalsScaffold();

for (const p of ['app/settings/page.tsx','app/account/upgrade/page.tsx']) {
  injectUIDebugFlag(p);
  ensureContainerWrapper(p);
  stripBigDebugBlocks(p);
}

console.log('OK: UI scaffold applied. Debug gated behind NEXT_PUBLIC_UI_DEBUG=1 (best-effort).');

import {readFile,writeFile} from 'node:fs/promises';
const here=new URL('.',import.meta.url);
const read=name=>readFile(new URL(name,here),'utf8');
const strip=text=>text.replace(/^import .*?;\n/gm,'').replace(/^export /gm,'');
const js=['data.mjs','engine.mjs','app.mjs'];
const code='const RESEARCH_NOTE='+JSON.stringify(await read('RESEARCH.md')).replace(/</g,'\\u003c')+';\n'+(await Promise.all(js.map(read))).map(strip).join('\n');
const html=(await read('index.template.html')).replace('/*__CSS__*/',await read('styles.css')).replace('/*__JS__*/',code);
await writeFile(new URL('index.html',here),html);
console.log(`Built ${Buffer.byteLength(html).toLocaleString()} bytes: cash-atlas/index.html (zero runtime dependencies)`);

const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const C = require('../site/calendar.js');
const events = [
  {id:'a',date:'2026-11-05',title:'Karaoke',description:'Bühne frei',category:'Karaoke',start:'21:00',doors:'18:30',source:'https://substanz-club.com/alle-events'},
  {id:'b',date:'2026-11-10',title:'Music Quiz',description:'Songs',category:'Quiz',start:'19:30',doors:'18:30',source:'https://substanz-club.com/alle-events'},
  {id:'c',date:'2026-11-04',title:'Bingo',description:'Glück',category:'Bingo',doors:'18:30',source:'https://substanz-club.com/alle-events'}
];
test('search, category, dates and reset ranges', () => {
  assert.equal(C.filtered(events,'','Alle','all','2026-11-05').length,2);
  assert.equal(C.filtered(events,'BÜHNE','Alle','all','2026-11-05')[0].id,'a');
  assert.equal(C.filtered(events,'','Quiz','week','2026-11-05')[0].id,'b');
  assert.equal(C.filtered(events,'','Alle','today','2026-11-05').length,1);
  assert.equal(C.filtered(events,'','Alle','past','2026-11-05')[0].id,'c');
  assert.equal(C.filtered(events,'absent','Alle','all','2026-11-05').length,0);
  assert.equal(C.filtered(events,'','Alle','month','2026-10-01').length,0);
});
test('Berlin date works independently of device timezone', () => assert.equal(C.today(new Date('2026-11-04T23:30:00Z')), '2026-11-05'));
test('single download has timezone, stable UID and correct escaping', () => {
  const result = C.single({...events[0],title:'Ä'.repeat(100)+',;\\'});
  assert.match(result,/DTSTART;TZID=Europe\/Berlin:20261105T210000/);
  assert.match(result,/BEGIN:VTIMEZONE/); assert.match(result,/UID:a/);
  assert.ok(result.split('\r\n').every(line => Buffer.byteLength(line) <= 75));
  assert.ok(result.replace(/\r\n /g,'').includes('\\,\\;\\\\'));
  assert.ok(C.single(events[2]).includes('Einlass\\; Beginn offen'));
});
test('manifest scope and all shell assets exist under project path', () => {
  const manifest = JSON.parse(fs.readFileSync('site/manifest.webmanifest'));
  assert.equal(manifest.start_url,'./'); assert.equal(manifest.scope,'./');
  for(const icon of manifest.icons) assert.ok(fs.existsSync('site/'+icon.src));
  const html = fs.readFileSync('site/index.html','utf8');
  for(const match of html.matchAll(/(?:href|src)="\.\/([^"#]+)"/g)) assert.ok(fs.existsSync('site/'+match[1]),match[1]);
});
test('service worker retains project scope, caches fallback and bypasses ICS', async () => {
  const handlers = {}, stored = new Map(); let offline = false;
  const cache = {addAll:async paths=>{for(const p of paths) stored.set(new URL(p,'https://example.test/substanz-events/').href,new Response('shell'));},put:async(req,res)=>stored.set(typeof req==='string'?req:req.url,res),match:async req=>stored.get(typeof req==='string'?req:req.href||req.url)};
  const context = {URL,Response,Error,caches:{open:async()=>cache,keys:async()=>[],delete:async()=>true},fetch:async()=>{if(offline)throw Error();return new Response('network');},self:{location:new URL('https://example.test/substanz-events/sw.js'),addEventListener:(name,fn)=>handlers[name]=fn,skipWaiting(){},clients:{claim:async()=>{}}}};
  vm.runInNewContext(fs.readFileSync('site/sw.js','utf8'),context);
  await new Promise(resolve=>handlers.install({waitUntil:p=>p.then(resolve)}));
  async function request(path,mode='cors') { let promise; handlers.fetch({request:{method:'GET',url:'https://example.test/substanz-events/'+path,mode},respondWith:p=>promise=p}); return promise; }
  assert.equal(await (await request('data/events.json')).text(),'network');
  offline=true;
  assert.equal(await (await request('data/events.json')).text(),'network');
  assert.equal(await (await request('unknown','navigate')).text(),'shell');
  assert.equal(await request('events.ics'),undefined);
});

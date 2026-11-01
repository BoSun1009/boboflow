// Run with NODE_PATH pointing to a temporary jsdom installation. Not a runtime dependency.
const {JSDOM,VirtualConsole}=require('jsdom');
const fs=require('node:fs'),assert=require('node:assert/strict');
const errors=[],exportBlobs=[];let downloaded;
const consoleProxy=new VirtualConsole();consoleProxy.on('jsdomError',e=>errors.push(e.message));
const dom=new JSDOM(fs.readFileSync(process.argv[2],'utf8'),{runScripts:'dangerously',pretendToBeVisual:true,virtualConsole:consoleProxy,beforeParse(w){w.URL.createObjectURL=blob=>{exportBlobs.push(blob);return 'blob:local-test'};w.URL.revokeObjectURL=()=>{};w.HTMLAnchorElement.prototype.click=function(){downloaded=this.download}}});
const w=dom.window,d=w.document,click=id=>d.getElementById(id).click();
assert.equal(d.documentElement.lang,'en');assert.match(d.querySelector('#surface').textContent,/Generate a draft/);assert.equal(d.querySelectorAll('#surface svg').length,1);
d.querySelector('[data-id="initial"]').dispatchEvent(new w.MouseEvent('click',{bubbles:true}));assert.equal(d.getElementById('drawer').hidden,false);assert.match(d.getElementById('detail').textContent,/Generate a draft/);
click('language');assert.equal(d.documentElement.lang,'zh-CN');assert.match(d.getElementById('detail').textContent,/生成工作流初稿/);assert.match(d.querySelector('#surface').textContent,/生成工作流初稿/);assert.equal(d.querySelectorAll('#surface svg').length,1);
click('theme');assert(d.body.classList.contains('dark'));assert.equal(d.getElementById('drawer').hidden,false);
click('export');assert.equal(downloaded,'boboflow-zh-dark.svg');assert.equal(exportBlobs.length,1);
click('reset');assert.equal(d.getElementById('drawer').hidden,true);assert.equal(d.querySelectorAll('#surface .dim').length,0);
const input=d.getElementById('search');input.value='不存在的步骤';input.dispatchEvent(new w.Event('input'));assert.match(d.getElementById('status').textContent,/没有匹配/);input.value='初稿';input.dispatchEvent(new w.Event('input'));assert.match(d.getElementById('status').textContent,/2 个匹配/);
click('walk');assert.equal(input.value,'');assert.match(d.getElementById('detail').textContent,/描述业务需求/);click('language');assert.match(d.getElementById('detail').textContent,/Describe the request/);click('walk');assert.match(d.getElementById('detail').textContent,/Generate a draft/);
w.document.dispatchEvent(new w.KeyboardEvent('keydown',{key:'Escape'}));assert.equal(d.getElementById('drawer').hidden,true);
click('stage');assert(d.body.classList.contains('stage'));click('export');assert.equal(downloaded,'boboflow-en-dark.svg');assert.equal(exportBlobs.length,2);assert.deepEqual(errors,[]);
Promise.all(exportBlobs.map(blob=>new Promise(resolve=>{const reader=new w.FileReader();reader.onload=()=>resolve(reader.result);reader.readAsText(blob)}))).then(texts=>{assert.match(texts[0],/生成工作流初稿/);assert.match(texts[1],/Generate a draft/);assert(!texts[0].includes('class="dim"'));console.log('DOM interaction checks passed: English default, bilingual SVG swap, preserved selection, themes, search, step-through, Escape, presentation and localized exportBlobs.');w.close()}).catch(e=>{console.error(e);w.close();process.exitCode=1});
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('app.js', 'utf8');
const resolver = source.slice(source.indexOf('async function resolveAnalysisServer'), source.indexOf("analyze.addEventListener('click', async"));
const healthy = () => ({ok:true, headers:new Headers({'content-type':'application/json'}), json:async()=>({status:'ok', service:'bridgelabs', market:'JobSpy / International'})});
function setup(fetch, origin='http://127.0.0.1:5500') {
 const url = new URL(origin);
 const context = vm.createContext({fetch, window:{location:url}, Error});
 vm.runInContext(resolver, context);
 return context.resolveAnalysisServer;
}
test('static preview discovers backend without uploading to static server', async () => {
 const urls = [];
 const resolve = setup(async url => {
   urls.push(url);
   return url.startsWith('http://127.0.0.1:5500') ? {ok:false, status:404} : healthy();
 });
 assert.equal(await resolve(new AbortController().signal), 'http://127.0.0.1:8000');
 assert.deepEqual(urls, ['http://127.0.0.1:5500/api/health','http://127.0.0.1:8000/api/health']);
});
test('backend-hosted frontend uses its own origin', async () => {
 const urls = [];
 const resolve = setup(async url => {urls.push(url); return healthy();}, 'http://127.0.0.1:8000');
 assert.equal(await resolve(new AbortController().signal),'http://127.0.0.1:8000');
 assert.equal(urls.length,1);
});
test('HTML responses produce actionable connection error', async () => {
 const resolve = setup(async () => ({ok:true, headers:new Headers({'content-type':'text/html'})}));
 await assert.rejects(resolve(new AbortController().signal), /Cannot reach Delta analysis/);
});
test('hosted websites never automatically send data to loopback backend', async () => {
 const urls = [];
 const resolve = setup(async url => {urls.push(url); return {ok:false};}, 'https://example.org');
 await assert.rejects(resolve(new AbortController().signal), /temporarily unavailable/);
 assert.deepEqual(urls,['https://example.org/api/health']);
});

import test from 'node:test';
import assert from 'node:assert/strict';
import {bondMetrics,bondDashboard} from '../bonds.js';

test('rates stay in percent while curve and credit spreads use basis points',()=>{
  const metrics=bondMetrics({nominal:{status:'ok',observations:[{date:'2026-11-20',yield2:4.63,yield10:4.92}]},credit:{status:'ok',observations:[{date:'2026-09-01',spread:.92},{date:'2026-10-01',spread:1.01}]}});
  assert.equal(metrics.find(m=>m.id==='y10').value,4.92);
  assert.ok(Math.abs(metrics.find(m=>m.id==='curve').value-29)<1e-8);
  assert.equal(metrics.find(m=>m.id==='credit').value,101);
  assert.equal(metrics.find(m=>m.id==='credit').delta,9);
  assert.equal(metrics.find(m=>m.id==='credit').monthly,true);
});
test('five-observation change is not confused with percentage growth or missing data',()=>{
  const observations=Array.from({length:6},(_,i)=>({date:`2026-11-${String(10+i).padStart(2,'0')}`,yield2:4+i*.02,yield10:4.5+i*.01}));
  const metrics=bondMetrics({nominal:{observations}});
  assert.equal(metrics.find(m=>m.id==='y10').delta,5);
  assert.equal(metrics.find(m=>m.id==='y2').delta,10);
  assert.equal(metrics.find(m=>m.id==='curve').delta,-5);
  assert.equal(metrics.find(m=>m.id==='real').value,null);
  assert.equal(bondMetrics()[0].delta,null);
});
test('old observations retain their original date and a warning in the dashboard',()=>{
  const html=bondDashboard({nominal:{status:'failed',observations:[{date:'2026-10-01',yield2:4,yield10:4.5}]}},'en','2026-11-21');
  assert.match(html,/Observation needs a fresh check/);
  assert.match(html,/Oct 1, 2026/);
  assert.match(html,/These are conditional scenarios/);
});

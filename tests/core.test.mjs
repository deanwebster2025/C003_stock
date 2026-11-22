import test from 'node:test';
import assert from 'node:assert/strict';
import {todayISO,addMonths,filterEvents,inWindow,toICS,safeURL} from '../core.js';

test('three calendar months clamp the day rather than overflow February',()=>{
  assert.equal(addMonths('2026-11-30',3),'2027-02-28');
  assert.equal(addMonths('2027-11-30',3),'2028-02-29');
  assert.equal(addMonths('2026-11-21',3),'2027-02-21');
});
test('the rolling window uses New York dates across UTC midnight and DST',()=>{
  assert.equal(todayISO(new Date('2026-11-22T02:00:00Z')),'2026-11-21');
  assert.equal(todayISO(new Date('2027-07-01T03:30:00Z')),'2027-06-30');
});
test('includes ongoing multi-day events and the boundary, excludes expired and cancelled',()=>{
  const e=(id,date,more={})=>({id,date,title:id,titleZh:id,impact:'high',category:'macro',...more});
  const items=[e('ongoing','2026-11-19',{endDate:'2026-11-22'}),e('past','2026-11-20'),e('last','2027-02-21'),e('outside','2027-02-22'),e('cancelled','2026-12-10',{lifecycle:'cancelled'})];
  assert.deepEqual(filterEvents(items,{today:'2026-11-21'}).map(e=>e.id),['ongoing','last']);
  assert.equal(inWindow(items[0],'2026-11-21','2027-02-21'),true);
});
test('search, bookmarks and categories combine without broadening results',()=>{
  const items=[{id:'fed',date:'2026-12-09',title:'Federal Reserve',titleZh:'美联储',tickers:['QQQ'],category:'centralbank',impact:'high'},{id:'other',date:'2026-12-10',title:'Other',tickers:['QQQ'],category:'earnings',impact:'medium'}];
  assert.deepEqual(filterEvents(items,{today:'2026-11-21',query:'美联储 QQQ',highOnly:true,savedOnly:true,saved:['fed']}).map(e=>e.id),['fed']);
  assert.equal(filterEvents(items,{today:'2026-11-21',category:'earnings',highOnly:true}).length,0);
});
test('calendar export preserves tentative dates and uses exclusive multi-day end',()=>{
  const events=[{id:'a',date:'2027-01-06',endDate:'2027-01-09',title:'CES, technology',titleZh:'消费电子展',summary:'Line 1\nLine 2',certainty:'tentative',sourceUrl:'https://example.com/'}];
  const ics=toICS(events,'en',new Date('2026-11-22T00:00:00Z'));
  assert.match(ics,/DTEND;VALUE=DATE:20270110/);assert.match(ics,/STATUS:TENTATIVE/);assert.match(ics,/CES\\, technology/);
  assert.equal(toICS([{...events[0],certainty:'window'}]).includes('BEGIN:VEVENT'),false);
});
test('untrusted URL schemes cannot become clickable links',()=>{assert.equal(safeURL('javascript:alert(1)'),'#');assert.equal(safeURL('https://www.bls.gov/'),'https://www.bls.gov/');});

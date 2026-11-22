import test from 'node:test';
import assert from 'node:assert/strict';
import {todayISO,addMonths,filterEvents,inWindow,toICS,safeURL,overviewMonths,windowEnd,recentStockNews} from '../core.js';

test('stock headlines age out in the browser even when the daily updater is unavailable',()=>{
  const now=new Date('2026-11-22T04:30:00Z');
  const news=['2026-11-19T04:30:00Z','2026-11-19T04:29:59Z','2026-11-22T04:30:01Z','invalid'].map(publishedAt=>({publishedAt}));
  assert.equal(recentStockNews(news,now).length,1);
  assert.equal(recentStockNews(news,new Date('2026-11-26T04:30:00Z')).length,0);
});

test('overview keeps both partial months and clips events to the rolling window',()=>{
  const events=[{id:'cross',date:'2026-11-30',endDate:'2026-12-02',impact:'high',certainty:'tentative'},{id:'boundary',date:'2027-02-21',impact:'medium',certainty:'confirmed'},{id:'outside',date:'2027-02-22'},{id:'cancelled',date:'2026-12-01',lifecycle:'cancelled'}];
  const months=overviewMonths(events,'2026-11-21','2027-02-21');
  assert.deepEqual(months.map(m=>m.first),['2026-11-01','2026-12-01','2027-01-01','2027-02-01']);
  assert.deepEqual(months.map(m=>m.events.length),[1,1,0,1]);
  assert.equal(months[0].days[19].active,false);
  assert.equal(months[1].days[0].events[0].id,'cross');
  assert.equal(months[1].days[0].high,true);
  assert.equal(months[1].days[0].tentative,true);
  assert.equal(months[3].days[20].events[0].id,'boundary');
  assert.equal(months[3].days[21].active,false);
  assert.equal(months[3].days[21].events.length,0);
});
test('short filters retain only their active dates in the overview',()=>{
  const end=windowEnd('2026-12-29','7d');
  assert.equal(end,'2027-01-04');
  const months=overviewMonths([],'2026-12-29',end);
  assert.equal(months.length,2);
  assert.equal(months.flatMap(m=>m.days).filter(d=>d.active).length,7);
});

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

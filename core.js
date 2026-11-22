export const ZONE = 'America/New_York';
export function todayISO(now = new Date()) {
  return new Intl.DateTimeFormat('en-CA', {timeZone: ZONE, year:'numeric', month:'2-digit', day:'2-digit'}).format(now);
}
export function parseDay(iso) { return new Date(`${iso}T12:00:00Z`); }
export function addDays(iso, days) {
  const d = parseDay(iso); d.setUTCDate(d.getUTCDate() + days); return d.toISOString().slice(0,10);
}
export function addMonths(iso, months) {
  const [y,m,d] = iso.split('-').map(Number);
  const target = new Date(Date.UTC(y,m-1+months,1,12));
  const last = new Date(Date.UTC(target.getUTCFullYear(), target.getUTCMonth()+1, 0)).getUTCDate();
  target.setUTCDate(Math.min(d,last)); return target.toISOString().slice(0,10);
}
export function dayDiff(a,b) { return Math.round((parseDay(b)-parseDay(a))/86400000); }
export function inWindow(event, start, end) {
  return event.date <= end && (event.endDate || event.date) >= start && !['cancelled','superseded'].includes(event.lifecycle);
}
export function filterEvents(events, {today=todayISO(), span='3m', query='', category='all', highOnly=false, savedOnly=false, saved=[], day=null}={}) {
  const end = span === '7d' ? addDays(today,6) : span === '30d' ? addDays(today,29) : addMonths(today,3);
  const terms = query.toLowerCase().trim().split(/\s+/).filter(Boolean);
  return events.filter(e => inWindow(e,today,end))
    .filter(e => category === 'all' || e.category === category)
    .filter(e => !highOnly || e.impact === 'high')
    .filter(e => !savedOnly || saved.includes(e.id))
    .filter(e => !day || e.date <= day && (e.endDate || e.date) >= day)
    .filter(e => terms.every(t => [e.title,e.titleZh,e.summary,e.summaryZh,...(e.tickers||[]),...(e.sectors||[])].join(' ').toLowerCase().includes(t)))
    .sort((a,b) => a.date.localeCompare(b.date) || (a.time || '99:99').localeCompare(b.time || '99:99') || a.title.localeCompare(b.title));
}
function icsEscape(s) { return String(s||'').replaceAll('\\','\\\\').replaceAll('\n','\\n').replaceAll(';','\\;').replaceAll(',','\\,'); }
function foldLine(s) {
  const lines=[]; let line='', length=0;
  for (const ch of s) { const size = new TextEncoder().encode(ch).length; if (length+size>73) {lines.push(line);line=' ';length=1;} line+=ch;length+=size; }
  lines.push(line);return lines.join('\r\n');
}
export function toICS(events, lang='en', now=new Date()) {
  const lines=['BEGIN:VCALENDAR','VERSION:2.0','PRODID:-//C003_stock//Market Events//EN','CALSCALE:GREGORIAN','X-WR-CALNAME:C003_stock'];
  const stamp=now.toISOString().replace(/[-:]/g,'').replace(/\.\d+Z/,'Z');
  for (const e of events.filter(e=>e.certainty!=='window')) {
    const label=lang==='zh'?(e.titleZh||e.title):e.title;
    const prefix=e.certainty==='tentative'?(lang==='zh'?'[暂定] ':'[Tentative] '):'';
    const desc=[lang==='zh'?(e.summaryZh||e.summary):e.summary,e.time?`${e.time} ${e.timezone||ZONE}`:e.timeLabel||'',e.sourceUrl,'All-day calendar reminder. Confirm the release time with the source.'].filter(Boolean).join('\n');
    lines.push('BEGIN:VEVENT',`UID:${icsEscape(e.id)}@c003-stock`,`DTSTAMP:${stamp}`,`DTSTART;VALUE=DATE:${e.date.replaceAll('-','')}`,`DTEND;VALUE=DATE:${addDays(e.endDate||e.date,1).replaceAll('-','')}`,`SUMMARY:${icsEscape(prefix+label)}`,`DESCRIPTION:${icsEscape(desc)}`,`URL:${icsEscape(e.sourceUrl)}`,`STATUS:${e.certainty==='tentative'?'TENTATIVE':'CONFIRMED'}`,'END:VEVENT');
  }
  lines.push('END:VCALENDAR'); return lines.map(foldLine).join('\r\n')+'\r\n';
}
export function safeURL(s) { try { const u=new URL(s);return ['https:','http:'].includes(u.protocol)?u.href:'#';}catch{return '#';} }
export function freshness(verifiedAt, today=todayISO()) {
  if(!verifiedAt) return 'unknown';
  const delta=dayDiff(verifiedAt.slice(0,10),today);
  return delta<=3?'fresh':delta<=14?'aging':'stale';
}

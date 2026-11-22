"""Daily, no-key collection of primary-source dates and clearly separated news context.

Run from any directory: python scripts/update_events.py
Failure policy: preserve last verified records, record check failure, never invent dates.
"""
from __future__ import annotations
import argparse
import calendar
from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import sys
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET
from zoneinfo import ZoneInfo

from catalog import SOURCES, RISKS, template
from stock_news import parse_stock_news, recent_news

ROOT=Path(__file__).resolve().parents[1]
MONTHS={m.lower():i for i,m in enumerate(calendar.month_name) if m}
MONTHS.update({m.lower():i for i,m in enumerate(calendar.month_abbr) if m})
DATE_RE=r'(?P<month>[A-Za-z]+)\.?\s+(?P<day>\d{1,2}),?\s+(?P<year>20\d{2})'

def utcnow():return datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z')
def today_et():return datetime.now(ZoneInfo('America/New_York')).date()
def add_months(d:date,n:int):
    y,m=divmod(d.year*12+d.month-1+n,12);m+=1
    return date(y,m,min(d.day,calendar.monthrange(y,m)[1]))
def normal(s):return re.sub(r'\s+',' ',unescape(s)).strip()
def slug(s):return re.sub(r'[^a-z0-9]+','-',s.lower()).strip('-')
def parse_date(s):
    m=re.search(DATE_RE,normal(s))
    if not m:raise ValueError('No full calendar date')
    return date(int(m['year']),MONTHS[m['month'].lower()],int(m['day'])).isoformat()

class Page(HTMLParser):
    """Extract text and table cells, without executing script or depending on a DOM library."""
    def __init__(self):
        super().__init__(convert_charrefs=True);self.parts=[];self.rows=[];self.row=None;self.cell=None;self.skip=0;self.heading=None;self.heading_parts=[];self.year=None
    def handle_starttag(self,tag,attrs):
        if tag in ('script','style'):self.skip+=1
        if tag in ('h2','h3','h4','caption'):self.heading=tag;self.heading_parts=[]
        if tag=='tr':self.row=[]
        if tag in ('td','th') and self.row is not None:self.cell=[]
    def handle_endtag(self,tag):
        if tag in ('script','style'):self.skip=max(0,self.skip-1)
        if tag==self.heading:
            h=normal(' '.join(self.heading_parts));m=re.fullmatch(r'(?:Table\s*:\s*|Year\s+)?(20\d{2})',h)
            if m:self.year=int(m[1])
            self.heading=None
        if tag in ('td','th') and self.cell is not None:
            self.row.append(normal(' '.join(self.cell)));self.cell=None
        if tag=='tr' and self.row is not None:
            self.rows.append((self.year,self.row));self.row=None
    def handle_data(self,s):
        if self.skip:return
        if s.strip():self.parts.append(s.strip())
        if self.cell is not None:self.cell.append(s)
        if self.heading:self.heading_parts.append(s)
    @property
    def text(self):return '\n'.join(self.parts)

def page(html):p=Page();p.feed(html);return p
def event(kind,id,d,src,now,**extra):
    e=template(kind)
    e.update(id=id,date=d,source=src['id'],sourceUrl=src['url'],certainty='confirmed',time='08:30' if kind in ('cpi','jobs','pce','gdp') else None,timezone='America/New_York',verifiedAt=now,verification='verified',origin='automatic',lifecycle='active')
    e.update(extra);return e

def collect_bls(html,src,now,today):
    result=[]
    for _,row in page(html).rows:
        if len(row)<3:continue
        try:d=parse_date(row[1])
        except (ValueError,KeyError):continue
        period=re.fullmatch(r'([A-Za-z]+)\s+(20\d{2})',row[0])
        if not period:continue
        key=f"{period[2]}-{MONTHS[period[1].lower()]:02}"
        e=event(src['kind'],f"{src['kind']}-{key}",d,src,now,referencePeriod=key)
        e['notes']=f'Reference period: {row[0]}. The event date is the publication date.'
        e['notesZh']=f'统计期：{key}。事件日期为公布日期。'
        tm=re.search(r'(\d{1,2}):(\d{2})\s*(AM|PM)',row[2],re.I)
        if tm:e['time']=f"{int(tm[1])%12+(12 if tm[3].upper()=='PM' else 0):02}:{tm[2]}"
        result.append(e)
    return result

def collect_bea(html,src,now,today):
    p=page(html);y=re.search(r'Year\s+(20\d{2})',p.text)
    if not y:raise ValueError('BEA calendar year was not found')
    year=int(y[1]);result=[]
    for _,row in p.rows:
        if len(row)<3:continue
        # The next-year table has an extra, frequently empty URL column.
        title=next((cell for cell in row[1:] if cell.startswith('Personal Income and Outlays,') or re.match(r'(GDP|Gross Domestic Product)\s*\(',cell)), '')
        kind='pce' if title.startswith('Personal Income and Outlays,') else 'gdp' if re.match(r'(GDP|Gross Domestic Product)\s*\(',title) else None
        if not kind:continue
        dm=re.search(r'([A-Za-z]+)\s+(\d{1,2})',row[0])
        if not dm or dm[1].lower() not in MONTHS:continue
        d=date(year,MONTHS[dm[1].lower()],int(dm[2])).isoformat()
        ident=kind+'-'+slug(title.replace('Personal Income and Outlays,',''))
        e=event(kind,ident,d,src,now,notes=title,notesZh='官方发布项目：'+title)
        if kind=='gdp':
            est='Advance' if 'Advance' in title else 'Second' if 'Second' in title else 'Third'
            e['title']=f'US GDP · {est.lower()} estimate';e['titleZh']='美国GDP · '+{'Advance':'初值','Second':'第二次估计','Third':'第三次估计'}[est]
            if est=='Advance':e['impact']='high'
        result.append(e)
    return result

def collect_fed(html,src,now,today):
    text=page(html).text
    blocks=re.split(r'(20\d{2})\s+FOMC Meetings',text);result=[]
    for i in range(1,len(blocks),2):
        year=int(blocks[i]);body=blocks[i+1]
        if year<today.year-1 or year>today.year+2:continue
        matches=list(re.finditer(r'\b(January|February|March|April|May|June|July|August|September|October|November|December|Jan/Feb|Apr/May|Oct/Nov)\s*\n\s*(\d{1,2})\s*[-–]\s*(\d{1,2})(\*?)',body))
        for n,m in enumerate(matches):
            tail=body[m.end():matches[n+1].start() if n+1<len(matches) else len(body)]
            if 'Monetary Policy Strategy Meeting' in tail:continue
            name=m[1].split('/')[-1];month=MONTHS[name.lower()];d=date(year,month,int(m[3])).isoformat()
            result.append(event('fed',f'fed-{year}-{month:02}',d,src,now,certainty='tentative',notes='Meeting dates remain tentative until confirmed at the preceding meeting. This is the decision day.',notesZh='会期需在前一次会议确认，所列为决议日。'))
    # A published meeting calendar is not proof that a future meeting has been confirmed.
    # Keep the calendar's explicit tentative designation until separately verified.
    return result

def collect_ecb(html,src,now,today):
    text=page(html).text;result=[]
    blocks=re.split(r'\b(\d{2}/\d{2}/20\d{2})\b',text)
    for i in range(1,len(blocks),2):
        body=blocks[i+1]
        if 'monetary policy meeting' not in body or 'Day 2' not in body:continue
        d=datetime.strptime(blocks[i],'%d/%m/%Y').date().isoformat()
        result.append(event('ecb','ecb-'+d,d,src,now,timezone='Europe/Berlin'))
    return result

def collect_boj(html,src,now,today):
    result=[]
    for year,row in page(html).rows:
        if not year or not row:continue
        m=re.match(r'([A-Za-z]+)\.?\s+(\d{1,2})\s*\([^)]*\),\s*(\d{1,2})\s*\(',row[0])
        if not m or m[1].lower() not in MONTHS:continue
        d=date(year,MONTHS[m[1].lower()],int(m[3])).isoformat()
        result.append(event('boj','boj-'+d,d,src,now,timezone='Asia/Tokyo'))
    return result

COLLECTORS={'fed':collect_fed,'bls':collect_bls,'bea':collect_bea,'ecb':collect_ecb,'boj':collect_boj}

def fetch(src):
    req=Request(src['url'],headers={'User-Agent':'Mozilla/5.0 (compatible; C003StockCalendar/1.0)','Accept':'text/html,application/rss+xml,application/xml;q=0.9,*/*;q=0.5'})
    with urlopen(req,timeout=22) as res:
        raw=res.read(3_000_001)
        if len(raw)>3_000_000:raise ValueError('Source exceeded the 3 MB limit')
        if raw.startswith(b'%PDF'):raise ValueError('PDF source requires editorial date verification')
        return raw.decode('utf-8-sig',errors='replace')

def parse_news(xml,now,today):
    root=ET.fromstring(xml);items=[];cutoff=datetime.combine(today-timedelta(days=10),datetime.min.time(),timezone.utc)
    for item in root.findall('.//item'):
        title=normal(item.findtext('title') or '');link=item.findtext('link') or '';pub=item.findtext('pubDate') or '';publisher=item.findtext('source') or ''
        try:dt=parsedate_to_datetime(pub);dt=dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
        except (ValueError,TypeError):continue
        if not title or urlparse(link).scheme not in ('https','http') or dt<cutoff or dt>datetime.now(timezone.utc)+timedelta(hours=3):continue
        items.append(dict(title=title,url=link,publisher=publisher,publishedAt=dt.isoformat()))
    seen=set();out=[]
    for n in sorted(items,key=lambda n:n['publishedAt'],reverse=True):
        if n['title'].lower() in seen:continue
        seen.add(n['title'].lower());out.append(n)
    return out[:5]

def collect_earnings(xml,src,now,today):
    result=[]
    for item in ET.fromstring(xml).findall('.//item'):
        title=normal(item.findtext('title') or '')
        if not re.search(r'to\s+(?:announce|report).*?(?:results|earnings)|sets\s+conference\s+call.*results',title,re.I):continue
        m=re.search(DATE_RE,title)
        if not m:continue
        d=parse_date(m[0])
        if not today.isoformat()<=d<=add_months(today,6).isoformat():continue
        link=item.findtext('link') or src['url'];host=urlparse(link).hostname or ''
        if not (host==src['allowedHost'] or host.endswith('.'+src['allowedHost'])):continue
        company=src['company'];e=event('earnings',f"{src['ticker'].lower()}-earnings-{d}",d,src,now,title=company+' earnings',titleZh=src['companyZh']+'财报',tickers=[src['ticker']],sourceUrl=link,notes=title,notesZh='公司原始公告：'+title)
        result.append(e)
    return result

def merge_calendar(existing,incoming,source_id,now,today):
    """Only retire missing dates within coverage proven by a successful parsed calendar."""
    merged={e['id']:deepcopy(e) for e in existing};changes=[]
    if not incoming:return list(merged.values()),changes
    lo=min(e['date'] for e in incoming);hi=max(e['date'] for e in incoming);ids={e['id'] for e in incoming}
    for old in merged.values():
        if old.get('source')==source_id and old.get('origin')=='automatic' and old['id'] not in ids and max(lo,today.isoformat())<=old['date']<=hi:
            # Absence is a review signal, not enough evidence to assert cancellation.
            old['verification']='review'
    for e in incoming:
        old=merged.get(e['id'])
        if old and old['date']!=e['date']:
            changes.append(dict(at=now,id=e['id'],message=f"{e['title']}: {old['date']} → {e['date']}",messageZh=f"{e['titleZh']}：{old['date']} → {e['date']}"))
        elif not old and today.isoformat()<=e['date']<=add_months(today,3).isoformat():
            changes.append(dict(at=now,id=e['id'],message=f"Added: {e['title']} · {e['date']}",messageZh=f"新增：{e['titleZh']} · {e['date']}"))
        merged[e['id']]=e
    return list(merged.values()),changes

def merge_curated(existing,curated):
    """Editorial status wins; verification belongs to the date actually checked."""
    merged={e['id']:deepcopy(e) for e in existing}
    for e in curated:
        copy=deepcopy(e);old=merged.get(e['id'])
        if old and (old['date'],old.get('endDate'))==(e['date'],e.get('endDate')):
            for key in ('verifiedAt','verification'):
                if key in old:copy[key]=old[key]
        elif old:
            copy.update(verifiedAt=None,verification='review')
        merged[e['id']]=copy
    return list(merged.values())

def validate(payload):
    ids=set()
    for e in payload['events']:
        if not e.get('id') or e['id'] in ids:raise ValueError('Duplicate or missing event ID')
        ids.add(e['id']);date.fromisoformat(e['date'])
        if e.get('endDate') and date.fromisoformat(e['endDate'])<date.fromisoformat(e['date']):raise ValueError('Event ends before its start')
        for key in ('title','titleZh','summary','summaryZh','source','sourceUrl','category','certainty','impact'):
            if not e.get(key):raise ValueError(f'{e["id"]}: missing {key}')
        if e['certainty'] not in ('confirmed','tentative','window'):raise ValueError('Invalid date certainty')
        if e['impact'] not in ('high','medium'):raise ValueError('Invalid impact')
        if urlparse(e['sourceUrl']).scheme!='https':raise ValueError('Event source must use HTTPS')
    if payload['windowMonths']!=3:raise ValueError('Window must be three calendar months')

def update(root=ROOT,include_news=True):
    now=utcnow();today=today_et();path=root/'data/events.json'
    existing=json.loads(path.read_text(encoding='utf-8'));curated=json.loads((root/'data/curated.json').read_text(encoding='utf-8'))
    previous_sources={s['id']:s for s in existing.get('sources',[])}
    watchlist_path=root/'data/watchlist.json'
    stocks=json.loads(watchlist_path.read_text(encoding='utf-8'))['stocks'] if watchlist_path.exists() else []
    previous_stocks={s['ticker']:s for s in existing.get('stocks',[])}
    for stock in stocks:
        old=previous_stocks.get(stock['ticker'],{})
        stock.update(news=recent_news(old.get('news',[]),now),newsCheckedAt=old.get('newsCheckedAt'),newsAttemptedAt=old.get('newsAttemptedAt'),newsStatus=old.get('newsStatus','pending'))
    # Current editorial configuration owns curated text; prior verification timestamps survive failed checks.
    events=merge_curated(existing.get('events',[]),curated['events'])
    old_risks={r['id']:r for r in existing.get('risks',[])};risks=deepcopy(RISKS)
    for r in risks:
        for k in ('news','newsCheckedAt','newsStatus'):
            if k in old_risks.get(r['id'],{}):r[k]=old_risks[r['id']][k]
    configs=deepcopy(SOURCES+curated['sources'])
    configs.append(dict(id='broadcom-announcements',name='Broadcom announcements',shortName='Broadcom IR',url='https://investors.broadcom.com/rss/news-releases.xml',parser='earnings',company='Broadcom',companyZh='博通',ticker='AVGO',allowedHost='broadcom.com',description='Discovers explicitly dated future earnings announcements.',descriptionZh='发现公司明确公布日期的未来财报公告。'))
    if include_news:
        for stock in stocks:
            configs.append(dict(id='stock-news-'+stock['ticker'],name='72-hour headlines · '+stock['ticker'],shortName='Google News RSS',parser='stock_news',ticker=stock['ticker'],url='https://news.google.com/rss/search?'+urlencode(dict(q=stock['query']+' when:3d',hl='en-US',gl='US',ceid='US:en')),description='Company-name search, a strict 72-hour publication window and title/link deduplication. Coverage is not exhaustive.',descriptionZh='按公司名称检索，严格过滤72小时发布时间并按标题及链接去重；不保证完整覆盖。'))
        for r in risks:
            configs.append(dict(id='news-'+r['id'],name='News context · '+r['title'],shortName='News search',parser='news',riskId=r['id'],url='https://news.google.com/rss/search?'+urlencode(dict(q=r['query']+' when:7d',hl='en-US',gl='US',ceid='US:en')),description='Google News RSS discovery; publisher links are context, never proof of a scheduled event.',descriptionZh='Google新闻RSS发现渠道；标题只作为背景，不用于确认未来事件日期。'))
    sources=[];changes=[];success=0;calendar_success=0
    with ThreadPoolExecutor(max_workers=8) as pool:
        tasks={pool.submit(fetch,s):s for s in configs}
        for future in as_completed(tasks):
            src=tasks[future];report={**src,'lastCheckedAt':now,'lastVerifiedAt':previous_sources.get(src['id'],{}).get('lastVerifiedAt'),'status':'failed'}
            try:
                raw=future.result();parser=src['parser']
                if parser in COLLECTORS:
                    incoming=COLLECTORS[parser](raw,src,now,today)
                    if not incoming:raise ValueError('No valid dated records parsed; source needs review')
                    events,delta=merge_calendar(events,incoming,src['id'],now,today);changes+=delta;calendar_success+=1;report['recordCount']=len(incoming)
                elif parser=='curated':
                    if not re.search(src['datePattern'],normal(page(raw).text),re.I):raise ValueError('Expected date text not found; editorial review required')
                    for e in events:
                        if e['source']==src['id']:e.update(verifiedAt=now,verification='verified')
                elif parser=='earnings':
                    incoming=collect_earnings(raw,src,now,today)
                    for e in incoming:
                        if not any(x['category']=='earnings' and x['date']==e['date'] and src['ticker'] in x.get('tickers',[]) for x in events):events.append(e)
                    report['recordCount']=len(incoming)
                elif parser=='news':
                    news=parse_news(raw,now,today)
                    for r in risks:
                        if r['id']==src['riskId']:r.update(news=news,newsCheckedAt=now,newsStatus='ok')
                    report['recordCount']=len(news)
                elif parser=='stock_news':
                    stock=next(s for s in stocks if s['ticker']==src['ticker'])
                    news=parse_stock_news(raw,stock,now)
                    stock.update(news=news,newsCheckedAt=now,newsAttemptedAt=now,newsStatus='ok')
                    report['recordCount']=len(news)
                report.update(status='ok',lastVerifiedAt=now);success+=1
            except Exception as exc:
                report['error']=str(exc)[:180]
                for e in events:
                    if e.get('source')==src['id']:e['verification']='review'
                if src['parser']=='news':
                    for r in risks:
                        if r['id']==src['riskId']:r['newsStatus']='failed'
                if src['parser']=='stock_news':
                    stock=next(s for s in stocks if s['ticker']==src['ticker'])
                    stock.update(newsStatus='failed',newsAttemptedAt=now)
                print(f"Source unavailable: {src['id']} ({type(exc).__name__})",file=sys.stderr)
            sources.append(report)
    cutoff=(today-timedelta(days=30)).isoformat()
    events=[e for e in events if (e.get('endDate') or e['date'])>=cutoff and e['date']<=add_months(today,15).isoformat()]
    events.sort(key=lambda e:(e['date'],e['title']))
    for r in risks:
        # Old news must not remain labelled recent when its provider fails.
        r['news']=[n for n in r.get('news',[]) if n.get('publishedAt','')[:10]>=(today-timedelta(days=10)).isoformat()]
    order={s['id']:i for i,s in enumerate(configs)};sources.sort(key=lambda s:order[s['id']])
    in_github=os.environ.get('GITHUB_ACTIONS')=='true'
    payload=dict(schemaVersion=1,updatedAt=now,timezone='America/New_York',windowMonths=3,automation={'active':in_github or existing.get('automation',{}).get('active',False),'provider':'GitHub Actions','scheduleUTC':'17 12 * * *'},refresh={'status':'ok' if success==len(configs) else 'partial' if calendar_success else 'failed','attemptedAt':now,'successCount':success,'sourceCount':len(configs),'calendarSourcesChecked':calendar_success},events=events,risks=risks,sources=sources,changes=(changes+existing.get('changes',[]))[:60])
    payload['stocks']=stocks
    validate(payload)
    temp=path.with_suffix('.tmp');temp.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');temp.replace(path)
    print(f"Updated {len(events)} dated records and {len(risks)} watch themes. {success}/{len(configs)} sources checked; {calendar_success} official calendars parsed.")
    return payload

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--no-news',action='store_true');parser.add_argument('--validate-only',action='store_true');args=parser.parse_args()
    if args.validate_only:
        data=json.loads((ROOT/'data/events.json').read_text());validate(data);print(f"Validated {len(data['events'])} events.")
    else:
        out=update(include_news=not args.no_news)
        if out['refresh']['status']=='failed':sys.exit(1)

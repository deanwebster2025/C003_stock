"""Public Treasury rates and the Fed's monthly GZ credit-spread research series."""
import csv
from datetime import datetime, timedelta
from io import StringIO
from math import isfinite

CREDIT_URL='https://www.federalreserve.gov/econres/notes/feds-notes/ebp_csv.csv'
CREDIT_NOTES='https://www.federalreserve.gov/econres/notes/feds-notes/updating-the-recession-risk-and-the-excess-bond-premium-20161006.html'


def bond_sources(today):
    sources=[]
    # The buffer preserves the chart and change calculations across New Year.
    for year in sorted({today.year, (today-timedelta(days=120)).year}):
        for kind,table in [('nominal','daily_treasury_yield_curve'),('real','daily_treasury_real_yield_curve')]:
            sources.append(dict(id=f'bond-{kind}-{year}',name=f'US Treasury · {kind} yields · {year}',shortName='US Treasury',
                url=f'https://home.treasury.gov/resource-center/data-chart-center/interest-rates/TextView?type={table}&field_tdr_date_value={year}',
                parser='bond_treasury',bondKind=kind,description='Daily par yields. Observation dates are separate from retrieval dates.',descriptionZh='国债日度收益率；观测日期与抓取日期分别显示。'))
    sources.append(dict(id='bond-credit',name='Federal Reserve · GZ corporate credit spread',shortName='Federal Reserve',url=CREDIT_URL,
        parser='bond_credit',bondKind='credit',description='Monthly staff research series, subject to revision; not a daily credit quote.',descriptionZh='月度研究序列，可能修订，不是每日信用利差报价。'))
    return sources


def number(value):
    try:
        result=float(value)
        return result if isfinite(result) else None
    except (TypeError,ValueError):
        return None


def parse_treasury(rows, kind):
    fields={'yield2':'2 yr','yield10':'10 yr'} if kind=='nominal' else {'real10':'10 yr'}
    columns=None
    result=[]
    for _,row in rows:
        if row and row[0].strip().lower()=='date':
            headers=[x.strip().lower() for x in row]
            if all(name in headers for name in fields.values()):
                columns={field:headers.index(name) for field,name in fields.items()}
            continue
        if columns is None or not row:
            continue
        try:
            observed=datetime.strptime(row[0],'%m/%d/%Y').date().isoformat()
            values={field:number(row[index]) for field,index in columns.items()}
        except (ValueError,IndexError):
            continue
        if any(value is None for value in values.values()):
            continue
        result.append(dict(date=observed,**values))
    if not result:
        raise ValueError('No valid Treasury observations; retain prior data')
    return result


def parse_credit(raw):
    reader=csv.DictReader(StringIO(raw.lstrip('\ufeff')))
    if not {'date','gz_spread'}.issubset(reader.fieldnames or []):
        raise ValueError('GZ credit-spread CSV columns changed')
    result=[]
    for row in reader:
        try:period=datetime.strptime(row['date'],'%Y-%m-%d').date().isoformat()
        except (ValueError,TypeError):continue
        spread=number(row['gz_spread'])
        if spread is not None:
            result.append(dict(date=period,spread=spread))
    if not result:
        raise ValueError('No valid monthly credit observations')
    return result


def merge_bonds(previous, incoming, reports, now, today):
    result={}
    for kind in ('nominal','real','credit'):
        old=previous.get(kind,{})
        cutoff=(today-timedelta(days=730 if kind=='credit' else 125)).isoformat()
        by_date={r['date']:r for r in old.get('observations',[])}
        for row in incoming.get(kind,[]):
            by_date[row['date']]=row
        observations=sorted((r for d,r in by_date.items() if cutoff<=d<=today.isoformat()),key=lambda r:r['date'])
        checks=[s for s in reports if s.get('bondKind')==kind]
        successful=sum(s['status']=='ok' for s in checks)
        status='ok' if checks and successful==len(checks) else 'partial' if successful else 'failed'
        result[kind]=dict(observations=observations,status=status,attemptedAt=now,
            lastSuccessAt=now if status=='ok' else old.get('lastSuccessAt'),frequency='monthly' if kind=='credit' else 'daily',
            sourceUrl=CREDIT_NOTES if kind=='credit' else next((s['url'] for s in reversed(checks)),old.get('sourceUrl')))
    return result

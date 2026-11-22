"""Bounded headline discovery; no sentiment model or automatic trade recommendations."""
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html import unescape
import re
from urllib.parse import urlparse
from xml.etree import ElementTree as ET


def instant(value):
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('A news timestamp needs an explicit timezone')
    return parsed.astimezone(timezone.utc)


def recent_news(items, now):
    end = instant(now)
    cutoff = end - timedelta(hours=72)
    valid = []
    for item in items:
        try:
            published = instant(item['publishedAt'])
        except (KeyError, ValueError, TypeError, AttributeError):
            continue
        if cutoff <= published <= end and urlparse(item.get('url', '')).scheme in ('http', 'https'):
            valid.append({**item, 'publishedAt': published.isoformat().replace('+00:00', 'Z')})
    return sorted(valid, key=lambda n: n['publishedAt'], reverse=True)


def parse_stock_news(xml, stock, now):
    root = ET.fromstring(xml)
    if root.tag not in ('rss', 'RDF', '{http://www.w3.org/1999/02/22-rdf-syntax-ns#}RDF'):
        raise ValueError('Expected an RSS news feed')
    items = []
    for item in root.findall('.//item'):
        title = re.sub(r'\s+', ' ', unescape(item.findtext('title') or '')).strip()
        publisher = (item.findtext('source') or '').strip()
        # A company alias is required: AA alone also means many unrelated things.
        if not any(re.search(r'\b' + re.escape(alias) + r'\b', title, re.I) for alias in stock['aliases']):
            continue
        if publisher and title.endswith(' - ' + publisher):
            title = title[:-len(' - ' + publisher)]
        try:
            dt = parsedate_to_datetime(item.findtext('pubDate') or '')
            if dt.tzinfo is None:
                continue
        except (ValueError, TypeError, OverflowError):
            continue
        items.append(dict(title=title, publisher=publisher, url=item.findtext('link') or '', publishedAt=dt.isoformat()))
    seen_titles, seen_urls, result = set(), set(), []
    for item in recent_news(items, now):
        key = re.sub(r'[^\w]+', '', item['title'].casefold())
        if key in seen_titles or item['url'] in seen_urls:
            continue
        seen_titles.add(key)
        seen_urls.add(item['url'])
        result.append(item)
    return result[:25]

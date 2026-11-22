from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from stock_news import parse_stock_news, recent_news

NOW='2026-11-22T04:30:00Z'


class StockNews(unittest.TestCase):
    def test_exact_72_hours_including_offset_and_future_rejection(self):
        items=[dict(title=str(i),url='https://example.com/'+str(i),publishedAt=dt) for i,dt in enumerate([
            '2026-11-19T04:30:00Z', '2026-11-19T04:29:59Z',
            '2026-11-18T23:30:00-05:00', '2026-11-22T04:30:01Z', 'bad', '2026-11-21T12:00:00'])]
        self.assertEqual({n['title'] for n in recent_news(items,NOW)},{'0','2'})

    def test_company_name_required_and_republished_titles_are_deduplicated(self):
        def item(title,url,publisher):
            return f'<item><title>{title} - {publisher}</title><link>{url}</link><source>{publisher}</source><pubDate>Fri, 20 Nov 2026 15:00:00 GMT</pubDate></item>'
        xml='<rss><channel>'+item('Alcoa production update','https://example.com/1','A')+item('Alcoa production update','https://example.com/2','B')+item('AA road travel','https://example.com/3','C')+item('Alcoa unsafe link','javascript:bad','D')+'</channel></rss>'
        news=parse_stock_news(xml,{'aliases':['Alcoa']},NOW)
        self.assertEqual(len(news),1)
        self.assertEqual(news[0]['title'],'Alcoa production update')

    def test_failed_provider_cache_expires_and_html_is_not_a_successful_feed(self):
        self.assertEqual(recent_news([dict(url='https://example.com',publishedAt='2026-11-18T12:00:00Z')],NOW),[])
        with self.assertRaises(ValueError):
            parse_stock_news('<html><body>Service unavailable</body></html>',{'aliases':['Alcoa']},NOW)


if __name__ == '__main__':
    unittest.main()

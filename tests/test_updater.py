from datetime import date
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from update_events import collect_bls,collect_bea,collect_fed,collect_boj,collect_ecb,collect_earnings,merge_calendar,merge_curated,parse_news,add_months,validate

NOW='2026-11-22T02:00:00Z';TODAY=date(2026,11,21)
def source(kind):return {'id':kind,'url':'https://example.com/','kind':kind}

class Collectors(unittest.TestCase):
 def test_editorial_cancellation_survives_previous_active_snapshot(self):
  old={'id':'a','date':'2026-12-01','lifecycle':'active','verification':'verified','verifiedAt':NOW}
  edited={**old,'lifecycle':'cancelled','verifiedAt':'2026-11-20'}
  merged=merge_curated([old],[edited])[0]
  self.assertEqual(merged['lifecycle'],'cancelled');self.assertEqual(merged['verifiedAt'],NOW)
 def test_changed_curated_date_cannot_inherit_old_verification(self):
  old={'id':'a','date':'2026-12-01','verification':'verified','verifiedAt':NOW}
  edited={**old,'date':'2026-12-02'}
  merged=merge_curated([old],[edited])[0]
  self.assertEqual(merged['verification'],'review');self.assertIsNone(merged['verifiedAt'])
 def test_bls_uses_release_date_not_reference_month(self):
  rows=collect_bls('<table><tr><td>December 2026</td><td>Jan. 13, 2027</td><td>08:30 AM</td></tr></table>',source('cpi'),NOW,TODAY)
  self.assertEqual(rows[0]['date'],'2027-01-13');self.assertEqual(rows[0]['id'],'cpi-2026-12');self.assertEqual(rows[0]['time'],'08:30')
 def test_bea_uses_calendar_year_and_excludes_state_gdp(self):
  html='<h2>Year 2027</h2><table><tr><td>January 28 8:30 AM</td><td>News</td><td>Personal Income and Outlays, December 2026</td></tr><tr><td>January 28 8:30 AM</td><td>News</td><td>GDP (Advance Estimate), 4th Quarter and Year 2026</td></tr><tr><td>January 29</td><td>News</td><td>GDP by County and Personal Income by County, 2025</td></tr></table>'
  rows=collect_bea(html,source('bea'),NOW,TODAY);self.assertEqual(len(rows),2);self.assertTrue(all(r['date']=='2027-01-28' for r in rows));self.assertEqual(rows[1]['impact'],'high')
 def test_fed_skips_strategy_meeting_and_takes_second_day(self):
  html='<h4>2027 FOMC Meetings</h4><div>January</div><div>26-27</div><div>October</div><div>26-27</div><div>Monetary Policy Strategy Meeting</div><div>November</div><div>16-17</div>'
  rows=collect_fed(html,source('fed'),NOW,TODAY);self.assertEqual([r['date'] for r in rows],['2027-01-27','2027-11-17']);self.assertEqual(rows[0]['certainty'],'tentative')
 def test_bea_next_year_table_can_have_an_empty_fourth_column(self):
  html='<h2>Year 2027</h2><table><tr><td>January 28 8:30 AM</td><td>News</td><td>Personal Income and Outlays, December 2026</td><td></td></tr></table>'
  rows=collect_bea(html,source('bea'),NOW,TODAY);self.assertEqual(len(rows),1);self.assertEqual(rows[0]['date'],'2027-01-28')
 def test_boj_respects_heading_year_not_minutes_year(self):
  html='<h2>2026</h2><table><tr><td>Dec. 17 (Thurs.), 18 (Fri.)</td><td>Jan. 27 (Wed.), 2027</td></tr></table><h2>2027</h2><table><tr><td>Jan. 21 (Thurs.), 22 (Fri.)</td></tr></table>'
  rows=collect_boj(html,source('boj'),NOW,TODAY);self.assertEqual([r['date'] for r in rows],['2026-12-18','2027-01-22'])
 def test_ecb_ignores_non_policy_and_day_one(self):
  html='<p>03/02/2027</p><p>monetary policy meeting (Day 1)</p><p>04/02/2027</p><p>monetary policy meeting (Day 2)</p><p>24/02/2027</p><p>non-monetary policy meeting</p>'
  self.assertEqual([r['date'] for r in collect_ecb(html,source('ecb'),NOW,TODAY)],['2027-02-04'])
 def test_missing_records_flag_review_instead_of_inventing_cancellation(self):
  old=[{'id':'a','date':'2026-12-01','source':'bls','origin':'automatic','verifiedAt':'2026-11-20'},{'id':'missing','date':'2026-12-10','source':'bls','origin':'automatic','verifiedAt':'2026-11-20'},{'id':'b','date':'2027-01-01','source':'bls','origin':'automatic','verifiedAt':'2026-11-20'}]
  new=[{**old[0],'verifiedAt':NOW},{**old[2],'verifiedAt':NOW}]
  merged,_=merge_calendar(old,new,'bls',NOW,TODAY);missing=next(e for e in merged if e['id']=='missing')
  self.assertEqual(missing['verification'],'review');self.assertEqual(missing['verifiedAt'],'2026-11-20');self.assertNotEqual(missing.get('lifecycle'),'cancelled')
 def test_rescheduled_event_replaces_prior_date_and_records_change(self):
  old=[{'id':'cpi-2026-12','date':'2027-01-13','source':'bls','origin':'automatic'}]
  incoming=[{**old[0],'date':'2027-01-14','title':'CPI','titleZh':'通胀'}]
  merged,changes=merge_calendar(old,incoming,'bls',NOW,TODAY);self.assertEqual(len(merged),1);self.assertEqual(merged[0]['date'],'2027-01-14');self.assertEqual(len(changes),1)
 def test_empty_failed_collection_does_not_erase_data(self):
  old=[{'id':'a','date':'2026-12-01','verifiedAt':'2026-11-20'}]
  self.assertEqual(merge_calendar(old,[],'bls',NOW,TODAY),(old,[]))
 def test_three_calendar_months_match_browser(self):
  self.assertEqual(add_months(date(2026,11,30),3),date(2027,2,28));self.assertEqual(add_months(date(2027,11,30),3),date(2028,2,29))
 def test_company_news_does_not_turn_past_results_into_future_earnings(self):
  src={**source('ir'),'company':'Broadcom','companyZh':'博通','ticker':'AVGO','allowedHost':'broadcom.com'}
  xml='<rss><channel><item><title>Broadcom to Announce Financial Results on December 9, 2026</title><link>https://investors.broadcom.com/result</link></item><item><title>Broadcom Announces Financial Results for December 9, 2026</title></item></channel></rss>'
  rows=collect_earnings(xml,src,NOW,TODAY);self.assertEqual(len(rows),1);self.assertEqual(rows[0]['date'],'2026-12-09')

if __name__=='__main__':unittest.main()

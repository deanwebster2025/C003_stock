from datetime import date
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from bond_market import bond_sources,parse_treasury,parse_credit,merge_bonds


class BondMarket(unittest.TestCase):
    def test_named_columns_skip_missing_values_without_shifting_maturities(self):
        rows=[(None,['Date','30 YR','2 Yr','10 Yr']),(None,['11/20/2026','5.31','4.63','4.92']),(None,['11/19/2026','5.4','N/A','5.04'])]
        self.assertEqual(parse_treasury(rows,'nominal'),[dict(date='2026-11-20',yield2=4.63,yield10=4.92)])
        self.assertEqual(parse_treasury([(None,['Date','5 YR','10 YR']),(None,['11/20/2026','2.53','2.77'])],'real')[0]['real10'],2.77)

    def test_credit_is_monthly_total_spread_not_excess_premium_or_probability(self):
        rows=parse_credit('date,gz_spread,ebp,est_prob\n2026-10-01,1.00456,-0.26533,0.11939\n2026-11-01,NaN,0,0\n')
        self.assertEqual(rows,[dict(date='2026-10-01',spread=1.00456)])
        with self.assertRaises(ValueError):parse_credit('date,other\n2026-10-01,1\n')

    def test_new_year_fetches_both_years_and_failed_fetch_retains_actual_date(self):
        today=date(2027,1,2)
        configs=bond_sources(today)
        self.assertEqual(len(configs),5)
        old={'nominal':{'observations':[dict(date='2026-12-31',yield2=4,yield10=4.5)],'lastSuccessAt':'2027-01-01T00:00:00Z'}}
        reports=[{**s,'status':'failed'} for s in configs]
        out=merge_bonds(old,{},reports,'2027-01-03T00:00:00Z',today)
        self.assertEqual(out['nominal']['observations'],old['nominal']['observations'])
        self.assertEqual(out['nominal']['lastSuccessAt'],old['nominal']['lastSuccessAt'])
        self.assertEqual(out['nominal']['status'],'failed')

    def test_revisions_replace_same_date_and_future_observations_are_excluded(self):
        old={'nominal':{'observations':[dict(date='2026-11-20',yield2=4,yield10=5)]}}
        incoming={'nominal':[dict(date='2026-11-20',yield2=4.63,yield10=4.92),dict(date='2027-01-01',yield2=1,yield10=2)]}
        out=merge_bonds(old,incoming,[dict(bondKind='nominal',status='ok',url='https://example.com')],'2026-11-22T04:50:00Z',date(2026,11,21))
        self.assertEqual(len(out['nominal']['observations']),1)
        self.assertEqual(out['nominal']['observations'][0]['yield2'],4.63)


if __name__=='__main__':unittest.main()

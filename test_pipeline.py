import sqlite3
import unittest
from pipeline import ingest,report,synthetic_export
class Checks(unittest.TestCase):
    def setUp(self): self.c=sqlite3.connect(':memory:')
    def tearDown(self): self.c.close()
    def test_repeat_is_idempotent(self):
        r=synthetic_export();a=ingest(self.c,r);b=ingest(self.c,list(reversed(r)))
        self.assertEqual(a,b);self.assertEqual(len(report(self.c)),9)
        self.assertEqual(self.c.execute('select count(*) from keyword_monthly').fetchone()[0],9)
    def test_late_snapshot_wins(self):
        r=synthetic_export();ingest(self.c,r)
        revised=[dict(x,searches=x['searches']+10,extracted_at='2026-04-02T00:00:00Z') for x in r]
        ingest(self.c,revised)
        self.assertEqual(sum(x[-1] for x in report(self.c)),sum(x['searches'] for x in revised))
    def test_invalid_does_not_partially_load(self):
        r=synthetic_export();ingest(self.c,r);before=report(self.c)
        with self.assertRaises(ValueError):ingest(self.c,r+[r[0]])
        with self.assertRaises(ValueError):ingest(self.c,[dict(r[0],searches=-1)])
        self.assertEqual(report(self.c),before)
    def test_geography_is_part_of_key(self):
        r=synthetic_export();ingest(self.c,r+[dict(x,geo='GB') for x in r]);self.assertEqual(len(report(self.c)),18)
    def test_invalid_dates_types_and_missing_fields(self):
        row=synthetic_export()[0]
        for patch in [dict(month='yesterday'),dict(month='2026-01-02'),dict(extracted_at='yesterday'),dict(extracted_at='2026-04-01T00:00:00'),dict(searches=True),dict(keyword=42),dict(searches=2**63)]:
            with self.assertRaises(ValueError):ingest(self.c,[dict(row,**patch)])
        del row['extracted_at']
        with self.assertRaises(ValueError):ingest(self.c,[row])
    def test_timezone_normalisation_and_tie_conflicts(self):
        row=synthetic_export()[0];a=ingest(self.c,[row])
        self.assertEqual(a,ingest(self.c,[dict(row,extracted_at='2026-04-01T02:00:00+02:00')]))
        with self.assertRaisesRegex(ValueError,'conflicting snapshot'):ingest(self.c,[dict(row,searches=999)])
        self.assertEqual(report(self.c)[0][-1],row['searches'])
        ingest(self.c,[dict(row,extracted_at='2026-03-31T23:30:00-01:00',searches=999)])
        self.assertEqual(report(self.c)[0][-1],999)
    def test_conflict_rejects_entire_batch(self):
        r=synthetic_export();ingest(self.c,r)
        with self.assertRaises(ValueError):ingest(self.c,[dict(r[0],geo='GB'),dict(r[1],searches=999)])
        self.assertEqual(self.c.execute('select count(*) from keyword_monthly').fetchone()[0],9)
if __name__=='__main__':unittest.main()

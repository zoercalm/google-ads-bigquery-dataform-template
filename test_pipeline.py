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
if __name__=='__main__':unittest.main()

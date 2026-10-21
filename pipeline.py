"""Synthetic Google Ads keyword-history ingestion; local SQLite demonstration."""
import argparse
import hashlib
import json
import sqlite3
from datetime import date,datetime,timezone
from pathlib import Path

DDL="""CREATE TABLE IF NOT EXISTS keyword_monthly (
 batch_id TEXT NOT NULL, keyword TEXT NOT NULL, geo TEXT NOT NULL, language TEXT NOT NULL,
 month TEXT NOT NULL, searches INTEGER NOT NULL CHECK(searches >= 0), extracted_at TEXT NOT NULL,
 PRIMARY KEY(batch_id,keyword,geo,language,month))"""

def synthetic_export():
    return [dict(keyword=k,geo='US',language='en',month=f'2026-{m:02d}-01',searches=50*m+i*20,
                 extracted_at='2026-04-01T00:00:00Z')
            for i,k in enumerate(['demo running shoes','demo walking boots','demo trainers']) for m in range(1,4)]

def normalise(rows):
    if not rows: raise ValueError('empty export')
    cleaned=[];keys=set()
    required={'keyword','geo','language','month','searches','extracted_at'}
    for r in rows:
        if not isinstance(r,dict) or set(r)!=required:raise ValueError('export fields must match the contract')
        for field in ('keyword','geo','language','month','extracted_at'):
            if not isinstance(r[field],str) or not r[field] or r[field]!=r[field].strip():raise ValueError('non-empty trimmed strings required')
        try:
            month=date.fromisoformat(r['month'])
            stamp=datetime.fromisoformat(r['extracted_at'].replace('Z','+00:00'))
            if month.isoformat()!=r['month'] or month.day!=1:raise ValueError('month must be YYYY-MM-01')
            if 'T' not in r['extracted_at'] or stamp.tzinfo is None or stamp.utcoffset() is None:raise ValueError('timestamp timezone required')
        except (ValueError,OverflowError) as exc:raise ValueError('invalid month or timezone timestamp') from exc
        if type(r['searches']) is not int or not 0<=r['searches']<=9223372036854775807:raise ValueError('searches must be a non-negative INT64')
        row=dict(r,extracted_at=stamp.astimezone(timezone.utc).isoformat(timespec='microseconds').replace('+00:00','Z'))
        key=tuple(row[k] for k in ('keyword','geo','language','month'))
        if key in keys:raise ValueError('duplicate key within export')
        keys.add(key);cleaned.append(row)
    return cleaned


def ingest(conn, rows):
    rows=normalise(rows)
    batch=hashlib.sha256(json.dumps(sorted(rows,key=lambda r:tuple(r[k] for k in ('keyword','geo','language','month'))),sort_keys=True).encode()).hexdigest()
    conn.execute(DDL)
    with conn:
        # An equal timestamp is the same snapshot, not an arbitrary hash tie-break.
        for r in rows:
            old=conn.execute('SELECT searches FROM keyword_monthly WHERE keyword=? AND geo=? AND language=? AND month=? AND extracted_at=?',
                tuple(r[k] for k in ('keyword','geo','language','month','extracted_at'))).fetchall()
            if any(v[0]!=r['searches'] for v in old):raise ValueError('conflicting snapshot: use a newer extracted_at for revisions')
        conn.executemany('INSERT OR IGNORE INTO keyword_monthly VALUES (?,?,?,?,?,?,?)',
                         [(batch,r['keyword'],r['geo'],r['language'],r['month'],r['searches'],r['extracted_at']) for r in rows])
    return batch

def report(conn):
    return conn.execute("""SELECT keyword,geo,language,month,searches FROM (
 SELECT *, ROW_NUMBER() OVER (PARTITION BY keyword,geo,language,month ORDER BY extracted_at DESC,batch_id DESC) AS n
 FROM keyword_monthly) WHERE n=1 ORDER BY keyword,month""").fetchall()

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--directory',default='output');args=p.parse_args()
    out=Path(args.directory);out.mkdir(parents=True,exist_ok=True)
    rows=normalise(synthetic_export())
    revised=normalise([dict(r,searches=r['searches']+10,extracted_at='2026-04-02T00:00:00Z') for r in rows])
    with sqlite3.connect(out/'demo.sqlite') as conn:
        batch=ingest(conn,rows);ingest(conn,rows)
        revised_batch=ingest(conn,revised)
        result=report(conn)
    (out/'keyword_monthly.ndjson').write_text(''.join(json.dumps(dict(batch_id=batch_id,**r))+'\n' for batch_id,export in [(batch,rows),(revised_batch,revised)] for r in export))
    (out/'report.json').write_text(json.dumps([dict(zip(('keyword','geo','language','month','searches'),r)) for r in result],indent=2)+'\n')
    print(f'2 snapshots x {len(rows)} synthetic rows; reruns kept {len(result)} reporting rows; revisions add 10 searches per key')
if __name__=='__main__':main()

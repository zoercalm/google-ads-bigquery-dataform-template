"""Synthetic Google Ads keyword-history ingestion; local SQLite demonstration."""
import argparse
import hashlib
import json
import sqlite3
from pathlib import Path

DDL="""CREATE TABLE IF NOT EXISTS keyword_monthly (
 batch_id TEXT NOT NULL, keyword TEXT NOT NULL, geo TEXT NOT NULL, language TEXT NOT NULL,
 month TEXT NOT NULL, searches INTEGER NOT NULL CHECK(searches >= 0), extracted_at TEXT NOT NULL,
 PRIMARY KEY(batch_id,keyword,geo,language,month))"""

def synthetic_export():
    return [dict(keyword=k,geo='US',language='en',month=f'2026-{m:02d}-01',searches=50*m+i*20,
                 extracted_at='2026-04-01T00:00:00Z')
            for i,k in enumerate(['demo running shoes','demo walking boots','demo trainers']) for m in range(1,4)]

def ingest(conn, rows):
    if not rows: raise ValueError('empty export')
    keys=set()
    for r in rows:
        key=tuple(r[k] for k in ('keyword','geo','language','month'))
        if key in keys: raise ValueError('duplicate key within export')
        keys.add(key)
        if not all(key) or type(r['searches']) is not int or r['searches']<0:
            raise ValueError('invalid export')
    batch=hashlib.sha256(json.dumps(sorted(rows,key=lambda r:tuple(r[k] for k in ('keyword','geo','language','month'))),sort_keys=True).encode()).hexdigest()
    conn.execute(DDL)
    with conn:
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
    rows=synthetic_export()
    with sqlite3.connect(out/'demo.sqlite') as conn:
        batch=ingest(conn,rows);ingest(conn,rows)
        result=report(conn)
    (out/'keyword_monthly.ndjson').write_text(''.join(json.dumps(dict(batch_id=batch,**r))+'\n' for r in rows))
    (out/'report.json').write_text(json.dumps(result,indent=2)+'\n')
    print(f'{len(rows)} synthetic source rows; rerun kept {len(result)} reporting rows')
if __name__=='__main__':main()

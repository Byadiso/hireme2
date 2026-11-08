"""Run one explicitly configured employer-form application locally, dry-run by default."""
import argparse,json,sqlite3
from hiremed.core import init_db
from hiremed.apply import submit_configured_form

def main():
    p=argparse.ArgumentParser();p.add_argument('job_id');p.add_argument('--config',default='application_sites.json');p.add_argument('--submit',action='store_true',help='Actually submit (requires all explicit gates)');args=p.parse_args()
    conn=init_db();row=conn.execute('SELECT id,title,company,url,assessment FROM jobs WHERE id=?',(args.job_id,)).fetchone()
    if not row:raise SystemExit('Job not found in private database')
    job={'id':row[0],'title':row[1],'company':row[2],'url':row[3]};assessment=json.loads(row[4]);result=submit_configured_form(conn,job,assessment,args.config,dry_run=not args.submit)
    print(json.dumps(result,indent=2));conn.close()
if __name__=='__main__':main()

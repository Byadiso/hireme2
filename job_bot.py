"""CLI adapter for scheduled discovery; dashboard calls the same service."""
import argparse,logging,os,sys
from dotenv import load_dotenv
load_dotenv()
from hiremed.discovery import discover
from hiremed.storage import load_profile

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--jobs-csv',help='Offline sample feed for testing')
    parser.add_argument('--limit',type=int,default=10)
    parser.add_argument('--roles',nargs='*')
    args=parser.parse_args()
    logging.basicConfig(level=logging.INFO,format='%(levelname)s %(message)s')
    if not args.jobs_csv and not (os.getenv('ADZUNA_APP_ID') and os.getenv('ADZUNA_APP_KEY')):
        raise SystemExit('Missing ADZUNA_APP_ID / ADZUNA_APP_KEY. Add repository Actions secrets and map them in the workflow.')
    profile=load_profile()
    if not profile:
        mode='PostgreSQL' if os.getenv('DATABASE_URL') else 'local SQLite'
        raise SystemExit(f'No saved CV profile in {mode}. Configure the same DATABASE_URL in the dashboard and GitHub Actions, then analyze and save your CV in the dashboard.')
    results=discover(profile,limit=args.limit,csv_path=args.jobs_csv,roles=args.roles)
    print('Analyzed %d jobs; %d fully verified matches; %d need review.'%(
        len(results),sum(bool(r['assessment'].get('eligible')) and r['policy']['allowed'] for r in results),
        sum(bool(r['policy']['unknown']) for r in results)))

if __name__=='__main__':main()

"""Batch experiments with identical instance, constraints and time budget."""
import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--dataset-dir',default='data/solomon')
    ap.add_argument('--output-dir',default='outputs/batch')
    ap.add_argument('--seconds',type=int,default=10)
    ap.add_argument('--repeats',type=int,default=1)
    ap.add_argument('--limit',type=int,default=None)
    args=ap.parse_args()
    files=sorted(p for p in Path(args.dataset_dir).iterdir() if p.suffix.lower() in ('.txt','.csv'))
    if not files: raise SystemExit('No datasets in '+args.dataset_dir)
    out=Path(args.output_dir);out.mkdir(parents=True,exist_ok=True)
    records=[]
    for path in files:
        for rep in range(args.repeats):
            target=out/f'{path.stem}_rep{rep+1}.json'
            cmd=[sys.executable,str(Path(__file__).with_name('experiment.py')),'--input',str(path),'--seconds',str(args.seconds),'--seed',str(42+rep),'--output',str(target)]
            if args.limit is not None: cmd += ['--limit',str(args.limit)]
            # CSV demo has no fleet metadata.
            if path.suffix.lower()=='.csv': cmd += ['--vehicles','3','--capacity','80']
            subprocess.run(cmd,check=True,capture_output=True,text=True)
            data=json.loads(target.read_text(encoding='utf-8'))
            for method,result in data['results'].items():
                records.append(dict(dataset=path.name,repeat=rep+1,method=method,status=result['status'],
                                    vehicles_used=result.get('vehicles_used',''),
                                    total_distance=result.get('total_distance',''),
                                    runtime_seconds=result['runtime_seconds'],
                                    customers=data['customers'],seconds=args.seconds))
    with (out/'summary.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=records[0].keys());writer.writeheader();writer.writerows(records)
    print('Saved:',out/'summary.csv')

if __name__=='__main__': main()

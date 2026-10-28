"""Draw distances for feasible runs only; no bar for failed algorithms."""
import argparse
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

def main():
    p=argparse.ArgumentParser();p.add_argument('--csv',default='outputs/batch/summary.csv');p.add_argument('--output',default='outputs/batch/distance.png');a=p.parse_args()
    df=pd.read_csv(a.csv)
    valid=df[df['status']=='feasible'].copy()
    if valid.empty:
        raise SystemExit('No feasible results to plot')
    pivot=valid.groupby(['dataset','method'])['total_distance'].mean().unstack()
    ax=pivot.plot(kind='bar',figsize=(max(8,len(pivot)*0.6),5),rot=45)
    ax.set_ylabel('Total Euclidean distance');ax.set_xlabel('Dataset');ax.set_title('VRPTW benchmark: feasible solutions only')
    plt.tight_layout();Path(a.output).parent.mkdir(parents=True,exist_ok=True);plt.savefig(a.output,dpi=160)
    print('Saved:',a.output)
if __name__=='__main__':main()

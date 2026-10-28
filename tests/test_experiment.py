import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from experiment import load, matrices, greedy, evaluate, read_solomon

ROOT=Path(__file__).resolve().parents[1]
class TestVRPTW(unittest.TestCase):
    def setUp(self):
        self.rows,_,_=load(ROOT/'data/sample.csv')
        self.d,self.t=matrices(self.rows,travel_scale=3)
    def test_baseline_feasible(self):
        result=greedy(self.rows,self.d,self.t,80,3)
        self.assertEqual(result['status'],'feasible')
        self.assertEqual(sum(len(r['stops']) for r in result['routes']),8)
    def test_capacity_rejection(self):
        with self.assertRaises(ValueError): evaluate([[1,2,3,4,5,6,7,8]],self.rows,self.d,self.t,80,3)
    def test_missing_customer_rejection(self):
        with self.assertRaises(ValueError): evaluate([[1]],self.rows,self.d,self.t,80,3)
    def test_solomon_parser(self):
        rows,v,c=read_solomon(ROOT/'data/examples/solomon_format_example.txt')
        self.assertEqual((len(rows),v,c),(4,2,100))
if __name__=='__main__':unittest.main()

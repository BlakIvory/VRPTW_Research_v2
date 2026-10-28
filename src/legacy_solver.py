"""VRPTW research demo: greedy feasible baseline and OR-Tools solver.
CSV columns: id,x,y,demand,ready,due,service. Depot is first row (id 0).
Distances are Euclidean and travel minutes = distance * minutes_per_distance.
"""
import argparse, csv, json, math, time
from pathlib import Path

def load_data(path):
    with open(path, newline='', encoding='utf-8-sig') as f:
        rows = [{k:float(v) if k not in ('id',) else int(v) for k,v in row.items()} for row in csv.DictReader(f)]
    if not rows or rows[0]['id'] != 0 or len(set(r['id'] for r in rows)) != len(rows):
        raise ValueError('First row must be depot id=0; ids must be unique')
    return rows

def matrices(rows, minutes_per_distance):
    n=len(rows)
    dist=[[math.hypot(a['x']-b['x'],a['y']-b['y']) for b in rows] for a in rows]
    travel=[[int(math.ceil(d*minutes_per_distance)) for d in r] for r in dist]
    return dist,travel

def summarize(routes, rows, dist, travel, capacity):
    results=[]; visited=[]
    for route in routes:
        if not route: continue
        t=rows[0]['ready']; load=0; km=0; prev=0; stops=[]
        for j in route:
            t=max(t+travel[prev][j],rows[j]['ready'])
            if t>rows[j]['due']: raise ValueError(f'Time window violated at {rows[j]["id"]}')
            load+=rows[j]['demand']; km+=dist[prev][j]
            stops.append({'id':rows[j]['id'],'arrival':round(t,1)})
            t+=rows[j]['service'];prev=j;visited.append(j)
        t+=travel[prev][0];km+=dist[prev][0]
        if load>capacity or t>rows[0]['due']: raise ValueError('Capacity/depot due violated')
        results.append({'route':[0]+[rows[j]['id'] for j in route]+[0], 'load':load,'distance':round(km,3),'return_time':round(t,1),'stops':stops})
    if sorted(visited)!=list(range(1,len(rows))): raise ValueError('Not all customers visited exactly once')
    return {'vehicles_used':len(results),'total_distance':round(sum(r['distance'] for r in results),3),'routes':results}

def greedy(rows,dist,travel,capacity,vehicles):
    unserved=set(range(1,len(rows))); routes=[]
    for _ in range(vehicles):
        route=[];prev=0;t=rows[0]['ready'];load=0
        while unserved:
            choices=[]
            for j in unserved:
                arrive=max(t+travel[prev][j],rows[j]['ready'])
                if load+rows[j]['demand']<=capacity and arrive<=rows[j]['due'] and arrive+rows[j]['service']+travel[j][0]<=rows[0]['due']:
                    choices.append((dist[prev][j],j,arrive))
            if not choices:break
            _,j,arrive=min(choices)
            route.append(j);unserved.remove(j);load+=rows[j]['demand'];t=arrive+rows[j]['service'];prev=j
        if route:routes.append(route)
        if not unserved:break
    if unserved:return {'status':'infeasible_or_greedy_failed','unserved':[rows[j]['id'] for j in sorted(unserved)]}
    return {'status':'feasible',**summarize(routes,rows,dist,travel,capacity)}

def optimize(rows,dist,travel,capacity,vehicles,seconds):
    try:
        from ortools.constraint_solver import pywrapcp, routing_enums_pb2
    except ImportError:
        return {'status':'missing_ortools','message':'Install: pip install ortools'}
    n=len(rows); manager=pywrapcp.RoutingIndexManager(n,vehicles,0); routing=pywrapcp.RoutingModel(manager)
    def distance_cb(i,j):return int(round(dist[manager.IndexToNode(i)][manager.IndexToNode(j)]*1000))
    distance_idx=routing.RegisterTransitCallback(distance_cb);routing.SetArcCostEvaluatorOfAllVehicles(distance_idx)
    def demand_cb(i):return int(rows[manager.IndexToNode(i)]['demand'])
    demand_idx=routing.RegisterUnaryTransitCallback(demand_cb)
    routing.AddDimensionWithVehicleCapacity(demand_idx,0,[int(capacity)]*vehicles,True,'Capacity')
    def time_cb(i,j):
        a=manager.IndexToNode(i);b=manager.IndexToNode(j)
        return travel[a][b]+int(rows[a]['service'])
    time_idx=routing.RegisterTransitCallback(time_cb)
    horizon=int(max(r['due'] for r in rows)+max(max(r) for r in travel)+max(r['service'] for r in rows))
    routing.AddDimension(time_idx,horizon,horizon,False,'Time')
    dim=routing.GetDimensionOrDie('Time')
    for node in range(1,n):
        idx=manager.NodeToIndex(node)
        dim.CumulVar(idx).SetRange(int(rows[node]['ready']),int(rows[node]['due']))
    for v in range(vehicles):
        dim.CumulVar(routing.Start(v)).SetRange(int(rows[0]['ready']),int(rows[0]['due']))
        dim.CumulVar(routing.End(v)).SetRange(int(rows[0]['ready']),int(rows[0]['due']))
    params=pywrapcp.DefaultRoutingSearchParameters()
    params.first_solution_strategy=routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    params.local_search_metaheuristic=routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    params.time_limit.seconds=max(1,seconds)
    sol=routing.SolveWithParameters(params)
    if sol is None:return {'status':'no_solution_found'}
    routes=[]
    for v in range(vehicles):
        idx=routing.Start(v);route=[]
        while not routing.IsEnd(idx):
            node=manager.IndexToNode(idx)
            if node!=0:route.append(node)
            idx=sol.Value(routing.NextVar(idx))
        if route:routes.append(route)
    return {'status':'feasible',**summarize(routes,rows,dist,travel,capacity)}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--data',default='sample.csv');ap.add_argument('--vehicles',type=int,default=3);ap.add_argument('--capacity',type=int,default=80);ap.add_argument('--minutes-per-distance',type=float,default=3);ap.add_argument('--seconds',type=int,default=5);ap.add_argument('--output',default='results.json')
    args=ap.parse_args();rows=load_data(args.data);dist,travel=matrices(rows,args.minutes_per_distance)
    output={'assumptions':{'distance':'Euclidean in coordinate units','travel':'ceil(distance * minutes_per_distance) minutes','single_depot':True,'service_times':'minutes'},'parameters':vars(args),'results':{}}
    for name,fn in [('greedy',lambda:greedy(rows,dist,travel,args.capacity,args.vehicles)),('ortools',lambda:optimize(rows,dist,travel,args.capacity,args.vehicles,args.seconds))]:
        start=time.perf_counter(); result=fn();result['runtime_seconds']=round(time.perf_counter()-start,4);output['results'][name]=result
    Path(args.output).write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(output['results'],ensure_ascii=False,indent=2));print('Saved',args.output)
if __name__=='__main__':main()

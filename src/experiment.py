"""VRPTW benchmark: Solomon or demo CSV; greedy and optional OR-Tools.
Run from project root: python src/experiment.py --input data/sample.csv --vehicles 3 --capacity 80
"""
import argparse
import csv
import json
import math
import re
import time
from pathlib import Path


def read_csv(path):
    with open(path, encoding='utf-8-sig', newline='') as f:
        raw = list(csv.DictReader(f))
    if not raw:
        raise ValueError('Empty CSV')
    return ([dict(id=int(r['id']), x=float(r['x']), y=float(r['y']), demand=int(r['demand']),
                  ready=int(r['ready']), due=int(r['due']), service=int(r['service'])) for r in raw], None, None)


def read_solomon(path):
    """Parse standard Solomon text: VEHICLE NUMBER CAPACITY and CUSTOMER CUST NO..."""
    lines = Path(path).read_text(encoding='utf-8-sig').splitlines()
    vehicle_count = capacity = None
    rows = []
    for i, line in enumerate(lines):
        if 'NUMBER' in line.upper() and 'CAPACITY' in line.upper():
            for nextline in lines[i+1:]:
                nums = re.findall(r'[-+]?\d+(?:\.\d+)?', nextline)
                if len(nums) >= 2:
                    vehicle_count, capacity = int(float(nums[0])), int(float(nums[1]))
                    break
            break
    for line in lines:
        parts = line.split()
        if len(parts) != 7:
            continue
        try:
            vals = [float(x) for x in parts]
        except ValueError:
            continue
        rows.append(dict(id=int(vals[0]), x=vals[1], y=vals[2], demand=int(vals[3]),
                         ready=int(vals[4]), due=int(vals[5]), service=int(vals[6])))
    if not rows or rows[0]['id'] != 0 or vehicle_count is None:
        raise ValueError('Invalid Solomon file: missing vehicle header or depot/customer rows')
    return rows, vehicle_count, capacity


def load(path):
    rows, vehicles, capacity = read_csv(path) if Path(path).suffix.lower() == '.csv' else read_solomon(path)
    if rows[0]['id'] != 0 or len({r['id'] for r in rows}) != len(rows):
        raise ValueError('Depot must be first row id=0; all IDs must be unique')
    if any(r['ready'] > r['due'] or r['demand'] < 0 or r['service'] < 0 for r in rows):
        raise ValueError('Invalid time window, demand or service')
    return rows, vehicles, capacity


def matrices(rows, distance_scale=1.0, travel_scale=1.0):
    # Solomon benchmarks normally use Euclidean distance and travel time on same scale.
    distance = [[math.hypot(a['x']-b['x'], a['y']-b['y'])*distance_scale for b in rows] for a in rows]
    travel = [[int(math.ceil(v*travel_scale - 1e-9)) for v in line] for line in distance]
    return distance, travel


def evaluate(routes, rows, distance, travel, capacity, fleet):
    """Independently verify all customers once, load, arrival, service, depot return."""
    if len(routes) > fleet:
        raise ValueError('Fleet exceeded')
    seen = []
    details = []
    for route in routes:
        t = rows[0]['ready']; load_used = 0; length = 0.0; prev = 0; stops = []
        for j in route:
            if j <= 0 or j >= len(rows):
                raise ValueError('Invalid customer index')
            arrival = t + travel[prev][j]
            service_start = max(arrival, rows[j]['ready'])
            if service_start > rows[j]['due']:
                raise ValueError('Time window exceeded')
            load_used += rows[j]['demand']
            length += distance[prev][j]
            stops.append(dict(customer_id=rows[j]['id'], arrival=arrival, service_start=service_start,
                              waiting=service_start-arrival))
            t = service_start + rows[j]['service']
            prev = j
            seen.append(j)
        t += travel[prev][0]
        length += distance[prev][0]
        if load_used > capacity or t > rows[0]['due']:
            raise ValueError('Vehicle capacity or depot closing time exceeded')
        details.append(dict(route=[0]+[rows[j]['id'] for j in route]+[0], load=load_used,
                            distance=round(length, 3), depot_return=t, stops=stops))
    if sorted(seen) != list(range(1, len(rows))):
        raise ValueError('Missing or duplicate customers')
    return dict(status='feasible', vehicles_used=len(routes), total_distance=round(sum(x['distance'] for x in details), 3), routes=details)


def greedy(rows, distance, travel, capacity, fleet):
    remaining = set(range(1, len(rows))); routes = []
    for _ in range(fleet):
        route = []; prev = 0; clock = rows[0]['ready']; load_used = 0
        while remaining:
            choices = []
            for j in remaining:
                start = max(clock+travel[prev][j], rows[j]['ready'])
                if (load_used+rows[j]['demand'] <= capacity and start <= rows[j]['due']
                        and start+rows[j]['service']+travel[j][0] <= rows[0]['due']):
                    choices.append((distance[prev][j], rows[j]['due'], j, start))
            if not choices:
                break
            _, _, j, start = min(choices)
            route.append(j); remaining.remove(j); load_used += rows[j]['demand']
            clock = start+rows[j]['service']; prev = j
        if route:
            routes.append(route)
        if not remaining:
            break
    if remaining:
        return dict(status='not_found', reason='Greedy could not serve all customers',
                    unserved=[rows[j]['id'] for j in sorted(remaining)])
    return evaluate(routes, rows, distance, travel, capacity, fleet)


def clarke_wright(rows, distance, travel, capacity, fleet):
    """Parallel Clarke-Wright savings with feasibility checks for each merge."""
    routes = [[j] for j in range(1, len(rows))]
    while len(routes) > fleet:
        candidates = []
        for a in range(len(routes)):
            for b in range(a + 1, len(routes)):
                ra, rb = routes[a], routes[b]
                # A merge is valid only when a customer endpoint of one route
                # can be joined to an endpoint of the other.
                variants = []
                if ra[-1] != 0 and rb[0] != 0:
                    variants.append(ra + rb)
                if rb[-1] != 0 and ra[0] != 0:
                    variants.append(rb + ra)
                if ra[0] != 0 and rb[0] != 0:
                    variants.append(list(reversed(ra)) + rb)
                if ra[-1] != 0 and rb[-1] != 0:
                    variants.append(ra + list(reversed(rb)))
                for merged in variants:
                    if sum(rows[j]['demand'] for j in merged) > capacity:
                        continue
                    clock = rows[0]['ready']; previous = 0; feasible = True
                    for customer in merged:
                        start = max(clock + travel[previous][customer], rows[customer]['ready'])
                        if start > rows[customer]['due']:
                            feasible = False
                            break
                        clock = start + rows[customer]['service']
                        previous = customer
                    if not feasible or clock + travel[previous][0] > rows[0]['due']:
                        continue
                    separate_length = (distance[0][ra[0]] + sum(distance[x][y] for x, y in zip(ra, ra[1:])) + distance[ra[-1]][0]
                                       + distance[0][rb[0]] + sum(distance[x][y] for x, y in zip(rb, rb[1:])) + distance[rb[-1]][0])
                    merged_length = distance[0][merged[0]] + sum(distance[x][y] for x, y in zip(merged, merged[1:])) + distance[merged[-1]][0]
                    saving = separate_length - merged_length
                    candidates.append((saving, merged, a, b))
        if not candidates:
            return dict(status='not_found', reason='Clarke-Wright could not merge routes into a feasible fleet',
                        routes_needed=len(routes), fleet=fleet)
        _, merged, a, b = max(candidates, key=lambda item: item[0])
        routes = [route for i, route in enumerate(routes) if i not in (a, b)] + [merged]
    return evaluate(routes, rows, distance, travel, capacity, fleet)


def ortools_solver(rows, distance, travel, capacity, fleet, seconds, seed):
    try:
        from ortools.constraint_solver import pywrapcp, routing_enums_pb2
    except ImportError:
        return dict(status='dependency_missing', reason='pip install ortools')
    n = len(rows)
    manager = pywrapcp.RoutingIndexManager(n, fleet, 0)
    routing = pywrapcp.RoutingModel(manager)
    def cost(i,j):
        return int(round(distance[manager.IndexToNode(i)][manager.IndexToNode(j)]*1000))
    ci = routing.RegisterTransitCallback(cost)
    routing.SetArcCostEvaluatorOfAllVehicles(ci)
    di = routing.RegisterUnaryTransitCallback(lambda i: rows[manager.IndexToNode(i)]['demand'])
    routing.AddDimensionWithVehicleCapacity(di, 0, [capacity]*fleet, True, 'Capacity')
    def transit(i,j):
        a = manager.IndexToNode(i); b = manager.IndexToNode(j)
        return travel[a][b] + rows[a]['service']
    ti = routing.RegisterTransitCallback(transit)
    horizon = max(r['due'] for r in rows) + max(map(max, travel)) + max(r['service'] for r in rows)
    routing.AddDimension(ti, horizon, horizon, False, 'Time')
    td = routing.GetDimensionOrDie('Time')
    for j in range(1,n):
        td.CumulVar(manager.NodeToIndex(j)).SetRange(rows[j]['ready'],rows[j]['due'])
    for v in range(fleet):
        td.CumulVar(routing.Start(v)).SetRange(rows[0]['ready'], rows[0]['due'])
        td.CumulVar(routing.End(v)).SetRange(rows[0]['ready'], rows[0]['due'])
        routing.AddVariableMinimizedByFinalizer(td.CumulVar(routing.Start(v)))
        routing.AddVariableMinimizedByFinalizer(td.CumulVar(routing.End(v)))
    params = pywrapcp.DefaultRoutingSearchParameters()
    params.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    params.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    params.time_limit.seconds = max(1, seconds)
    # OR-Tools RoutingSearchParameters has no stable random_seed across all versions.
    solution = routing.SolveWithParameters(params)
    if solution is None:
        return dict(status='not_found', reason='No solution found within time limit')
    routes=[]
    for v in range(fleet):
        index=routing.Start(v); route=[]
        while not routing.IsEnd(index):
            node=manager.IndexToNode(index)
            if node: route.append(node)
            index=solution.Value(routing.NextVar(index))
        if route: routes.append(route)
    return evaluate(routes,rows,distance,travel,capacity,fleet)


def main():
    ap=argparse.ArgumentParser(description='Run VRPTW benchmark on Solomon TXT or CSV')
    ap.add_argument('--input',required=True)
    ap.add_argument('--vehicles',type=int,default=None)
    ap.add_argument('--capacity',type=int,default=None)
    ap.add_argument('--limit',type=int,default=None,help='Number of customers (for development only)')
    ap.add_argument('--seconds',type=int,default=10)
    ap.add_argument('--travel-scale',type=float,default=1.0)
    ap.add_argument('--seed',type=int,default=42)
    ap.add_argument('--output',default='outputs/result.json')
    args=ap.parse_args()
    rows, file_vehicles, file_capacity = load(args.input)
    if args.limit is not None: rows=rows[:args.limit+1]
    fleet=args.vehicles if args.vehicles is not None else file_vehicles
    capacity=args.capacity if args.capacity is not None else file_capacity
    if fleet is None or capacity is None or fleet<1 or capacity<1:
        ap.error('Provide positive --vehicles and --capacity for CSV')
    if args.travel_scale<=0: ap.error('travel-scale must be positive')
    distance, travel=matrices(rows,travel_scale=args.travel_scale)
    results={}
    for name,method in [('greedy',lambda:greedy(rows,distance,travel,capacity,fleet)),
                        ('ortools',lambda:ortools_solver(rows,distance,travel,capacity,fleet,args.seconds,args.seed))]:
        start=time.perf_counter()
        try: result=method()
        except Exception as exc: result=dict(status='error',reason=str(exc))
        result['runtime_seconds']=round(time.perf_counter()-start,5)
        results[name]=result
    report=dict(dataset=Path(args.input).name, customers=len(rows)-1, vehicles_available=fleet,
                capacity=capacity, seed=args.seed, seconds=args.seconds, travel_scale=args.travel_scale,
                distance_metric='Euclidean', time_metric='ceil(Euclidean * travel_scale)',
                results=results)
    target=Path(args.output);target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:{key:value for key,value in v.items() if key!='routes'} for k,v in results.items()},indent=2))
    print('Saved:',target)

if __name__=='__main__': main()

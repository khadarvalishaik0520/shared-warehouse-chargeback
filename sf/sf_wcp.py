"""Snowflake helpers for the calibration runs (credentials only from ~/.snowflake/connections.toml, connection [cdexp])."""
import os, sys, json, time
import snowflake.connector
HERE = os.path.dirname(os.path.abspath(__file__))
# Six TPC-H-style reporting statements (run on schema TPCH10 of the database CDEXP; see README).
BATCH = [
    ('pricing_summary', "SELECT l_returnflag, l_linestatus, sum(l_quantity) AS sum_qty, sum(l_extendedprice) AS sum_base_price, sum(l_extendedprice * (1 - l_discount)) AS sum_disc_price, avg(l_quantity) AS avg_qty, count(*) AS count_order FROM lineitem WHERE l_shipdate <= DATE '2024-09-01' GROUP BY l_returnflag, l_linestatus ORDER BY l_returnflag, l_linestatus"),
    ('shipping_priority', "SELECT l_orderkey, sum(l_extendedprice * (1 - l_discount)) AS revenue, o_orderdate, o_shippriority FROM customer, orders, lineitem WHERE c_mktsegment = 'BUILDING' AND c_custkey = o_custkey AND l_orderkey = o_orderkey AND o_orderdate < DATE '2024-06-01' AND l_shipdate > DATE '2024-06-01' GROUP BY l_orderkey, o_orderdate, o_shippriority ORDER BY revenue DESC LIMIT 10"),
    ('revenue_by_nation', "SELECT n_name, sum(l_extendedprice * (1 - l_discount)) AS revenue FROM customer, orders, lineitem, supplier, nation WHERE c_custkey = o_custkey AND l_orderkey = o_orderkey AND l_suppkey = s_suppkey AND c_nationkey = s_nationkey AND s_nationkey = n_nationkey AND o_orderdate >= DATE '2023-01-01' AND o_orderdate < DATE '2024-01-01' GROUP BY n_name ORDER BY revenue DESC"),
    ('order_priority_checking', "SELECT o_orderpriority, count(*) AS order_count FROM orders WHERE o_orderdate >= DATE '2023-07-01' AND o_orderdate < DATE '2023-10-01' AND EXISTS ( SELECT 1 FROM lineitem WHERE l_orderkey = o_orderkey AND l_shipdate < DATE '2023-10-15' ) GROUP BY o_orderpriority ORDER BY o_orderpriority"),
    ('top_suppliers_by_cost', 'SELECT s_name, sum(ps_supplycost * ps_availqty) AS total_value FROM supplier, partsupp, nation WHERE s_suppkey = ps_suppkey AND s_nationkey = n_nationkey GROUP BY s_name ORDER BY total_value DESC LIMIT 20'),
    ('part_type_profit', 'SELECT p_type, sum(l_extendedprice * (1 - l_discount) - ps_supplycost * l_quantity) AS profit FROM lineitem, part, partsupp WHERE l_partkey = p_partkey AND ps_partkey = p_partkey AND l_suppkey = ps_suppkey GROUP BY p_type ORDER BY profit DESC'),
]

def connect(warehouse, tag, schema="TPCH10"):
    return snowflake.connector.connect(connection_name="cdexp", warehouse=warehouse, database="CDEXP", schema=schema,
        session_parameters={"USE_CACHED_RESULT": False, "QUERY_TAG": tag, "STATEMENT_TIMEOUT_IN_SECONDS": 300})

def run(con, sql):
    cur = con.cursor(); t = time.time()
    try:
        cur.execute(sql); cur.fetchall(); return {"ok": True, "qid": cur.sfqid, "client_s": time.time() - t, "t0": t}
    except Exception as e:
        return {"ok": False, "qid": getattr(cur, "sfqid", None), "client_s": time.time() - t, "t0": t, "err": str(e)[:200]}

def batch_queries():
    return list(BATCH)

def warehouse_ok(con, wh):
    cur = con.cursor(); cur.execute("show warehouses like '%s'" % wh); r = cur.fetchall()
    if not r: return "MISSING"
    cols = [c[0] for c in cur.description]; d = dict(zip(cols, r[0]))
    return "%s size=%s auto_suspend=%s monitor=%s" % (d["state"], d["size"], d["auto_suspend"], d.get("resource_monitor"))

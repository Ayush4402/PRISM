-- =====================================================================
-- Fixed |AUX| = 8, k = 2..8 branches, 1X data: all 8 TPC-H tables, chain key k = 1..1000.
-- Every join column of chain k equals k, so every join in every branch matches and every branch is FIT.
-- Branches: consecutive segments of the FK path region-nation-supplier-partsupp-part-lineitem-orders-customer (see fixed_aux_workload.py)
-- Set the schema in config.ini to: fixaux_1x
-- =====================================================================
DROP SCHEMA IF EXISTS fixaux_1x CASCADE;
CREATE SCHEMA fixaux_1x;

CREATE TABLE fixaux_1x.region (r_regionkey int NOT NULL, r_name char(25) NOT NULL, r_comment varchar(152) NOT NULL);
CREATE TABLE fixaux_1x.nation (n_nationkey int NOT NULL, n_name char(25) NOT NULL, n_regionkey int NOT NULL, n_comment varchar(152) NOT NULL);
CREATE TABLE fixaux_1x.supplier (s_suppkey int NOT NULL, s_name char(25) NOT NULL, s_address varchar(40) NOT NULL, s_nationkey int NOT NULL, s_phone char(15) NOT NULL, s_acctbal numeric(15,2) NOT NULL, s_comment varchar(101) NOT NULL);
CREATE TABLE fixaux_1x.customer (c_custkey int NOT NULL, c_name varchar(25) NOT NULL, c_address varchar(40) NOT NULL, c_nationkey int NOT NULL, c_phone char(15) NOT NULL, c_acctbal numeric(15,2) NOT NULL, c_mktsegment char(10) NOT NULL, c_comment varchar(117) NOT NULL);
CREATE TABLE fixaux_1x.part (p_partkey int NOT NULL, p_name varchar(55) NOT NULL, p_mfgr char(25) NOT NULL, p_brand char(10) NOT NULL, p_type varchar(25) NOT NULL, p_size int NOT NULL, p_container char(10) NOT NULL, p_retailprice numeric(15,2) NOT NULL, p_comment varchar(23) NOT NULL);
CREATE TABLE fixaux_1x.partsupp (ps_partkey int NOT NULL, ps_suppkey int NOT NULL, ps_availqty int NOT NULL, ps_supplycost numeric(15,2) NOT NULL, ps_comment varchar(199) NOT NULL);
CREATE TABLE fixaux_1x.orders (o_orderkey int NOT NULL, o_custkey int NOT NULL, o_orderstatus char(1) NOT NULL, o_totalprice numeric(15,2) NOT NULL, o_orderdate date NOT NULL, o_orderpriority char(15) NOT NULL, o_clerk char(15) NOT NULL, o_shippriority int NOT NULL, o_comment varchar(79) NOT NULL);
CREATE TABLE fixaux_1x.lineitem (l_orderkey int NOT NULL, l_partkey int NOT NULL, l_suppkey int NOT NULL, l_linenumber int NOT NULL, l_quantity numeric(15,2) NOT NULL, l_extendedprice numeric(15,2) NOT NULL, l_discount numeric(15,2) NOT NULL, l_tax numeric(15,2) NOT NULL, l_returnflag char(1) NOT NULL, l_linestatus char(1) NOT NULL, l_shipdate date NOT NULL, l_commitdate date NOT NULL, l_receiptdate date NOT NULL, l_shipinstruct char(25) NOT NULL, l_shipmode char(10) NOT NULL, l_comment varchar(44) NOT NULL);

-- chain k has one row in every table; all join columns equal k
INSERT INTO fixaux_1x.region   SELECT k, 'REGION' || k, 'c' FROM generate_series(1, 1000) k;
INSERT INTO fixaux_1x.nation   SELECT k, 'NATION' || k, k, 'c' FROM generate_series(1, 1000) k;
INSERT INTO fixaux_1x.supplier SELECT k, 'Supplier#' || k, 'addr' || k, k, '10-000-000-0001', 1000 + (k % 5000), 'c' FROM generate_series(1, 1000) k;
INSERT INTO fixaux_1x.customer SELECT k, 'Customer#' || k, 'addr' || k, k, '20-000-000-0001', 2000 + (k % 5000), 'BUILDING', 'c' FROM generate_series(1, 1000) k;
INSERT INTO fixaux_1x.part     SELECT k, 'part' || k, 'M#1', 'Brand#1', 'T', 1, 'SM BOX', 900 + (k % 1000), 'c' FROM generate_series(1, 1000) k;
INSERT INTO fixaux_1x.partsupp SELECT k, k, 10, 1.00, 'c' FROM generate_series(1, 1000) k;
INSERT INTO fixaux_1x.orders   SELECT k, k, 'O', 1000.00 + (k % 1000), DATE '1995-01-01', '3-MEDIUM', 'Clerk#1', 0, 'c' FROM generate_series(1, 1000) k;
INSERT INTO fixaux_1x.lineitem SELECT k, k, k, 1, 10, 100.00, 0.05, 0.02, 'N', 'O',
       DATE '1995-01-02', DATE '1995-01-03', DATE '1995-01-04', 'NONE', 'AIR', 'c' FROM generate_series(1, 1000) k;

-- validity: every distinct branch used by UK2..UK8 returns rows
DO $$
DECLARE b text; n bigint;
BEGIN
  PERFORM set_config('search_path', 'fixaux_1x, pg_catalog', true);
  FOREACH b IN ARRAY ARRAY[
    'SELECT r_name, r_regionkey FROM region, nation, supplier, partsupp WHERE r_regionkey = n_regionkey AND n_nationkey = s_nationkey AND s_suppkey = ps_suppkey',
    'SELECT p_name, p_retailprice FROM part, lineitem, orders, customer WHERE p_partkey = l_partkey AND l_orderkey = o_orderkey AND o_custkey = c_custkey',
    'SELECT r_name, r_regionkey FROM region, nation, supplier WHERE r_regionkey = n_regionkey AND n_nationkey = s_nationkey',
    'SELECT ps_comment, ps_supplycost FROM partsupp, part, lineitem WHERE ps_partkey = p_partkey AND p_partkey = l_partkey',
    'SELECT o_clerk, o_totalprice FROM orders, customer WHERE o_custkey = c_custkey',
    'SELECT r_name, r_regionkey FROM region, nation WHERE r_regionkey = n_regionkey',
    'SELECT s_name, s_acctbal FROM supplier, partsupp WHERE s_suppkey = ps_suppkey',
    'SELECT p_name, p_retailprice FROM part, lineitem WHERE p_partkey = l_partkey',
    'SELECT o_clerk, o_totalprice FROM orders',
    'SELECT c_name, c_acctbal FROM customer',
    'SELECT p_name, p_retailprice FROM part',
    'SELECT l_comment, l_extendedprice FROM lineitem',
    'SELECT s_name, s_acctbal FROM supplier',
    'SELECT ps_comment, ps_supplycost FROM partsupp',
    'SELECT r_name, r_regionkey FROM region',
    'SELECT n_name, n_nationkey FROM nation'] LOOP
    EXECUTE 'SELECT count(*) FROM (' || b || ') q' INTO n;
    IF n = 0 THEN RAISE EXCEPTION 'branch returns no rows: %', b; END IF;
  END LOOP;
END $$;

ANALYZE;
SELECT count(*) AS total_rows FROM (
  SELECT 1 FROM fixaux_1x.region UNION ALL SELECT 1 FROM fixaux_1x.nation UNION ALL SELECT 1 FROM fixaux_1x.supplier
  UNION ALL SELECT 1 FROM fixaux_1x.customer UNION ALL SELECT 1 FROM fixaux_1x.part UNION ALL SELECT 1 FROM fixaux_1x.partsupp
  UNION ALL SELECT 1 FROM fixaux_1x.orders UNION ALL SELECT 1 FROM fixaux_1x.lineitem) t;
-- expected: 0 primary keys, 0 foreign keys
SELECT count(*) FILTER (WHERE contype = 'p') AS primary_keys, count(*) FILTER (WHERE contype = 'f') AS foreign_keys
FROM pg_constraint WHERE connamespace = 'fixaux_1x'::regnamespace;
-- cleanup: DROP SCHEMA fixaux_1x CASCADE;

-- Drops all primary-key, foreign-key and unique constraints in one schema (foreign keys first).
-- Use it on schemas that already exist (e.g. nep_scale, oj_scale). Change the schema name below.
DO $$
DECLARE r record; s text := 'fixaux_1x';
BEGIN
  FOR r IN SELECT conrelid::regclass AS t, conname FROM pg_constraint
           WHERE connamespace = s::regnamespace AND contype IN ('f', 'p', 'u')
           ORDER BY contype  -- 'f' sorts before 'p' and 'u'
  LOOP
    EXECUTE format('ALTER TABLE %s DROP CONSTRAINT %I', r.t, r.conname);
  END LOOP;
END $$;

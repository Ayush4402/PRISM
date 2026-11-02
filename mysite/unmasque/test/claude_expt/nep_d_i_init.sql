-- =====================================================================
-- NEP scaling workload: ONE lineitem table, 10 queries with 1..10 NEPs.
-- Query k = SELECT * FROM lineitem WHERE nep_1 AND ... AND nep_k
-- Every query is extractable from the same table because each NEP_i has a
-- witness row that violates ONLY NEP_i (all other NEP columns hold values
-- that satisfy their NEPs). Such a row works for every k >= i.
-- =====================================================================
DROP SCHEMA IF EXISTS nep_scale CASCADE;
DROP TABLE IF EXISTS nep_workload;
DROP TABLE IF EXISTS nep;
CREATE SCHEMA nep_scale;

CREATE TABLE nep_scale.lineitem (
  l_orderkey int NOT NULL, l_partkey int NOT NULL, l_suppkey int NOT NULL, l_linenumber int NOT NULL,
  l_quantity numeric(15,2) NOT NULL, l_extendedprice numeric(15,2) NOT NULL,
  l_discount numeric(15,2) NOT NULL, l_tax numeric(15,2) NOT NULL,
  l_returnflag char(1) NOT NULL, l_linestatus char(1) NOT NULL,
  l_shipdate date NOT NULL, l_commitdate date NOT NULL, l_receiptdate date NOT NULL,
  l_shipinstruct char(25) NOT NULL, l_shipmode char(10) NOT NULL, l_comment varchar(44) NOT NULL,
  PRIMARY KEY (l_orderkey, l_linenumber));

-- ---------- the 10 NEPs (attribute <> value) ----------
CREATE TABLE nep (idx int PRIMARY KEY, attr text, val text);
INSERT INTO nep VALUES
 (1,  'l_quantity',      '25'),
 (2,  'l_extendedprice', '5000.00'),
 (3,  'l_discount',      '0.05'),
 (4,  'l_tax',           '0.04'),
 (5,  'l_returnflag',    '''R'''),
 (6,  'l_linestatus',    '''F'''),
 (7,  'l_shipinstruct',  '''COLLECT COD'''),
 (8,  'l_shipmode',      '''AIR'''),
 (9,  'l_shipdate',      'DATE ''1995-06-15'''),
 (10, 'l_commitdate',    'DATE ''1995-07-01''');

-- ---------- data ----------
-- "normal" row: satisfies all 10 NEPs
--   qty 10, price 1000, disc 0.02, tax 0.02, flag A, status O,
--   shipdate 1994-03-10, commitdate 1994-04-10, instruct NONE, mode TRUCK
-- witness i = normal row with ONLY column i set to the NEP value.
INSERT INTO nep_scale.lineitem VALUES
 (101,1,1,1, 10,1000.00,0.02,0.02,'A','O','1994-03-10','1994-04-10','1994-05-10','NONE','TRUCK','c'), -- satisfies all
 (1,1,1,1,   25,1000.00,0.02,0.02,'A','O','1994-03-10','1994-04-10','1994-05-10','NONE','TRUCK','c'), -- witness NEP1
 (2,1,1,1,   10,5000.00,0.02,0.02,'A','O','1994-03-10','1994-04-10','1994-05-10','NONE','TRUCK','c'), -- witness NEP2
 (3,1,1,1,   10,1000.00,0.05,0.02,'A','O','1994-03-10','1994-04-10','1994-05-10','NONE','TRUCK','c'), -- witness NEP3
 (4,1,1,1,   10,1000.00,0.02,0.04,'A','O','1994-03-10','1994-04-10','1994-05-10','NONE','TRUCK','c'), -- witness NEP4
 (5,1,1,1,   10,1000.00,0.02,0.02,'R','O','1994-03-10','1994-04-10','1994-05-10','NONE','TRUCK','c'), -- witness NEP5
 (6,1,1,1,   10,1000.00,0.02,0.02,'A','F','1994-03-10','1994-04-10','1994-05-10','NONE','TRUCK','c'), -- witness NEP6
 (7,1,1,1,   10,1000.00,0.02,0.02,'A','O','1994-03-10','1994-04-10','1994-05-10','COLLECT COD','TRUCK','c'), -- witness NEP7
 (8,1,1,1,   10,1000.00,0.02,0.02,'A','O','1994-03-10','1994-04-10','1994-05-10','NONE','AIR','c'),   -- witness NEP8
 (9,1,1,1,   10,1000.00,0.02,0.02,'A','O','1995-06-15','1994-04-10','1994-05-10','NONE','TRUCK','c'), -- witness NEP9
 (10,1,1,1,  10,1000.00,0.02,0.02,'A','O','1994-03-10','1995-07-01','1994-05-10','NONE','TRUCK','c'); -- witness NEP10

-- extra rows that satisfy all NEPs (change 1000 to scale the table; k is the only thing that varies)
INSERT INTO nep_scale.lineitem
SELECT 1000 + g, 1, 1, 1, 10, 1000.00, 0.02, 0.02, 'A', 'O',
       DATE '1994-03-10', DATE '1994-04-10', DATE '1994-05-10', 'NONE', 'TRUCK', 'c'
FROM generate_series(1, 1000) g;

-- ---------- workload: 10 queries, k = 1..10 NEPs ----------
-- Unqualified table name: set search_path / config schema to nep_scale when running PRISM.
CREATE TABLE nep_workload AS
SELECT k, 'SELECT * FROM lineitem WHERE ' ||
          string_agg(attr || ' <> ' || val, ' AND ' ORDER BY idx) AS sql
FROM generate_series(1, 10) k JOIN nep ON nep.idx <= k
GROUP BY k ORDER BY k;

-- ---------- validity check: every query returns rows, and each of its NEPs has a witness ----------
DO $$
DECLARE kk int; ii int; n bigint;
BEGIN
  FOR kk IN 1..10 LOOP
    EXECUTE (SELECT 'SELECT count(*) FROM nep_scale.lineitem WHERE ' ||
                    string_agg(attr || ' <> ' || val, ' AND ' ORDER BY idx)
             FROM nep WHERE idx <= kk) INTO n;
    IF n = 0 THEN RAISE EXCEPTION 'query % returns no rows', kk; END IF;
    FOR ii IN 1..kk LOOP
      EXECUTE (SELECT 'SELECT count(*) FROM nep_scale.lineitem WHERE ' ||
                      string_agg(CASE WHEN idx = ii THEN attr || ' = ' || val
                                      ELSE attr || ' <> ' || val END, ' AND ' ORDER BY idx)
               FROM nep WHERE idx <= kk) INTO n;
      IF n = 0 THEN RAISE EXCEPTION 'query %: NEP % has no witness', kk, ii; END IF;
    END LOOP;
  END LOOP;
END $$;

SELECT k, sql FROM nep_workload ORDER BY k;   -- the 10 queries
-- cleanup: DROP SCHEMA nep_scale CASCADE; DROP TABLE nep_workload, nep;

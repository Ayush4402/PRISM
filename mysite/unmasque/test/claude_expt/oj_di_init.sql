-- =====================================================================
-- Outer-join scaling on the real TPC-H tables (needs prism_make_schema from the first script).
-- Query k = region LEFT OUTER JOIN ... (k joins over the path in oj_spec), k = 1..7.
-- =====================================================================
DROP TABLE IF EXISTS oj_workload;
DROP TABLE IF EXISTS oj_spec;
SELECT prism_make_schema('oj_scale');          -- empty TPC-H schema (drops/recreates oj_scale)

-- path position, table, a key column of it, projected column, ON condition joining it to the previous table
CREATE TABLE oj_spec (pos int PRIMARY KEY, tab text, key_col text, proj_col text, on_cond text);
INSERT INTO oj_spec VALUES
 (1,'region',  'r_regionkey','r_name',      NULL),
 (2,'nation',  'n_nationkey','n_name',      'r_regionkey = n_regionkey'),
 (3,'supplier','s_suppkey',  's_name',      'n_nationkey = s_nationkey'),
 (4,'partsupp','ps_partkey', 'ps_availqty', 's_suppkey = ps_suppkey'),
 (5,'part',    'p_partkey',  'p_name',      'ps_partkey = p_partkey'),
 (6,'lineitem','l_orderkey', 'l_quantity',  'p_partkey = l_partkey'),
 (7,'orders',  'o_orderkey', 'o_totalprice','l_orderkey = o_orderkey'),
 (8,'customer','c_custkey',  'c_name',      'o_custkey = c_custkey');

CREATE OR REPLACE FUNCTION oj_scale.regen(p_filler int) RETURNS void LANGUAGE plpgsql AS $$
DECLARE kk int; jj int; n bigint; from_txt text;
BEGIN
  TRUNCATE oj_scale.region, oj_scale.nation, oj_scale.supplier, oj_scale.customer,
           oj_scale.part, oj_scale.partsupp, oj_scale.orders, oj_scale.lineitem;

  -- chain id k, chain length len (= number of tables on the path that have a row)
  CREATE TEMP TABLE _ch ON COMMIT DROP AS
    SELECT g AS k, g AS len FROM generate_series(1,7) g              -- witness chains 1..7
    UNION ALL SELECT 8, 8                                             -- fully matched chain
    UNION ALL SELECT 1000 + g, 8 FROM generate_series(1, p_filler) g; -- filler chains

  INSERT INTO oj_scale.region   SELECT k, 'REGION'||k, 'c' FROM _ch WHERE len >= 1;
  INSERT INTO oj_scale.nation   SELECT k, 'NATION'||k, k, 'c' FROM _ch WHERE len >= 2;
  INSERT INTO oj_scale.supplier SELECT k, 'Supplier#'||k, 'a', k, '10-000-000-0001', 100.00, 'c' FROM _ch WHERE len >= 3;
  INSERT INTO oj_scale.partsupp SELECT k, k, k, 1.00, 'c' FROM _ch WHERE len >= 4;
  INSERT INTO oj_scale.part     SELECT k, 'part'||k, 'M#1', 'Brand#1', 'T', 1, 'SM BOX', 900.00, 'c' FROM _ch WHERE len >= 5;
  INSERT INTO oj_scale.lineitem SELECT k, k, k, 1, k, 100.00, 0.05, 0.02, 'N', 'O',
        DATE '1995-01-02', DATE '1995-01-03', DATE '1995-01-04', 'NONE', 'AIR', 'c' FROM _ch WHERE len >= 6;
  INSERT INTO oj_scale.orders   SELECT k, k, 'O', k + 0.5, DATE '1995-01-01', '3-MEDIUM', 'Clerk#1', 0, 'c' FROM _ch WHERE len >= 7;
  INSERT INTO oj_scale.customer SELECT k, 'Customer#'||k, 'a', 1, '20-000-000-0001', 100.00, 'BUILDING', 'c' FROM _ch WHERE len >= 8;

  -- validity: each query has a fully matched row, and each of its joins has an unmatched witness
  FOR kk IN 1..7 LOOP
    SELECT 'oj_scale.region' || string_agg(format(' LEFT OUTER JOIN oj_scale.%s ON %s', tab, on_cond), '' ORDER BY pos)
      INTO from_txt FROM oj_spec WHERE pos BETWEEN 2 AND kk + 1;
    EXECUTE format('SELECT count(*) FROM %s WHERE %s IS NOT NULL', from_txt,
                   (SELECT key_col FROM oj_spec WHERE pos = kk + 1)) INTO n;
    IF n = 0 THEN RAISE EXCEPTION 'query %: no fully matched row', kk; END IF;
    FOR jj IN 1..kk LOOP
      EXECUTE format('SELECT count(*) FROM %s WHERE %s IS NOT NULL AND %s IS NULL', from_txt,
                     (SELECT key_col FROM oj_spec WHERE pos = jj),
                     (SELECT key_col FROM oj_spec WHERE pos = jj + 1)) INTO n;
      IF n = 0 THEN RAISE EXCEPTION 'query %: join % has no unmatched witness', kk, jj; END IF;
    END LOOP;
  END LOOP;
END $$;

SELECT oj_scale.regen(1000);            -- base: 36 + 8,000 = 8,036 rows in total across the tables
ANALYZE;

-- the 7 queries (unqualified names: set search_path / config schema to oj_scale)
CREATE TABLE oj_workload AS
SELECT k,
  'SELECT ' || (SELECT string_agg(proj_col, ', ' ORDER BY pos) FROM oj_spec WHERE pos <= k + 1)
  || ' FROM region' || (SELECT string_agg(format(' LEFT OUTER JOIN %s ON %s', tab, on_cond), '' ORDER BY pos)
                        FROM oj_spec WHERE pos BETWEEN 2 AND k + 1) || ';' AS sql
FROM generate_series(1, 7) k;

SELECT k, sql FROM oj_workload ORDER BY k;
-- cleanup: DROP SCHEMA oj_scale CASCADE; DROP TABLE oj_workload, oj_spec;

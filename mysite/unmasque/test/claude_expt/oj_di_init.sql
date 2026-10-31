CREATE OR REPLACE FUNCTION oj_scale.regen(p_filler int) RETURNS void LANGUAGE plpgsql AS $$
DECLARE kk int; jj int; n bigint; from_txt text;
BEGIN
  TRUNCATE oj_scale.region, oj_scale.nation, oj_scale.supplier, oj_scale.customer,
           oj_scale.part, oj_scale.partsupp, oj_scale.orders, oj_scale.lineitem;

  -- chain k has a row in every table whose path position lies in [lo, hi]
  DROP TABLE IF EXISTS _ch;
  CREATE TEMP TABLE _ch ON COMMIT DROP AS
    SELECT g AS k, 1 AS lo, g AS hi FROM generate_series(1,7) g        -- left-side witnesses (end at join g)
    UNION ALL SELECT 8, 1, 8                                           -- fully matched chain
    UNION ALL SELECT 2000 + g, g + 1, 8 FROM generate_series(1,7) g    -- right-side orphans (start after join g)
    UNION ALL SELECT 1000 + g, 1, 8 FROM generate_series(1, p_filler) g;  -- filler, fully matched

  INSERT INTO oj_scale.region   SELECT k, 'REGION'||k, 'c' FROM _ch WHERE lo <= 1 AND hi >= 1;
  INSERT INTO oj_scale.nation   SELECT k, 'NATION'||k, k, 'c' FROM _ch WHERE lo <= 2 AND hi >= 2;
  INSERT INTO oj_scale.supplier SELECT k, 'Supplier#'||k, 'a', k, '10-000-000-0001', 100.00, 'c' FROM _ch WHERE lo <= 3 AND hi >= 3;
  INSERT INTO oj_scale.partsupp SELECT k, k, k, 1.00, 'c' FROM _ch WHERE lo <= 4 AND hi >= 4;
  INSERT INTO oj_scale.part     SELECT k, 'part'||k, 'M#1', 'Brand#1', 'T', 1, 'SM BOX', 900.00, 'c' FROM _ch WHERE lo <= 5 AND hi >= 5;
  INSERT INTO oj_scale.lineitem SELECT k, k, k, 1, k, 100.00, 0.05, 0.02, 'N', 'O',
        DATE '1995-01-02', DATE '1995-01-03', DATE '1995-01-04', 'NONE', 'AIR', 'c' FROM _ch WHERE lo <= 6 AND hi >= 6;
  INSERT INTO oj_scale.orders   SELECT k, k, 'O', k + 0.5, DATE '1995-01-01', '3-MEDIUM', 'Clerk#1', 0, 'c' FROM _ch WHERE lo <= 7 AND hi >= 7;
  INSERT INTO oj_scale.customer SELECT k, 'Customer#'||k, 'a', 1, '20-000-000-0001', 100.00, 'BUILDING', 'c' FROM _ch WHERE lo <= 8 AND hi >= 8;

  -- validity 1: each query has a fully matched row, and each of its joins has a left-side unmatched witness
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

  -- validity 2: every join edge also has a right-side orphan (row in table j+1 with no partner in table j)
  FOR jj IN 1..7 LOOP
    EXECUTE format('SELECT count(*) FROM oj_scale.%s WHERE NOT EXISTS (SELECT 1 FROM oj_scale.%s WHERE %s)',
                   (SELECT tab FROM oj_spec WHERE pos = jj + 1),
                   (SELECT tab FROM oj_spec WHERE pos = jj),
                   (SELECT on_cond FROM oj_spec WHERE pos = jj + 1)) INTO n;
    IF n = 0 THEN RAISE EXCEPTION 'join %: no right-side orphan', jj; END IF;
  END LOOP;
END $$;

SELECT oj_scale.regen(1000);   -- base: 36 witness/full rows + 28 orphan rows + 8,000 filler rows = 8,064 rows
ANALYZE;

CREATE OR REPLACE FUNCTION oj_scale.regen(
  p_filler       int,               -- number of bulk chains
  p_scale        int DEFAULT 1,     -- multiplier for witness / full / orphan chains
  p_mismatch_pct int DEFAULT 30     -- % of bulk chains that are partial (stop early / start late)
) RETURNS void LANGUAGE plpgsql AS $$
DECLARE kk int; jj int; n bigint; from_txt text;
BEGIN
  TRUNCATE oj_scale.region, oj_scale.nation, oj_scale.supplier, oj_scale.customer,
           oj_scale.part, oj_scale.partsupp, oj_scale.orders, oj_scale.lineitem;

  -- chain k has a row in every table whose path position lies in [lo, hi]
  DROP TABLE IF EXISTS _ch;
  CREATE TEMP TABLE _ch ON COMMIT DROP AS
  WITH bulk AS (
    SELECT g,
           abs(hashtext('s'||g)::bigint) % 100     AS s,   -- partial vs. matched
           1 + abs(hashtext('a'||g)::bigint) % 8   AS a,   -- random segment endpoints
           1 + abs(hashtext('b'||g)::bigint) % 8   AS b
    FROM generate_series(1, p_filler) g
  ),
  raw(id, lo, hi) AS (
    -- left-side witnesses: chain ends at join g (rows in 1..g only), p_scale copies each
    SELECT 'W'||g||'_'||r, 1, g
      FROM generate_series(1,7) g, generate_series(1,p_scale) r
    UNION ALL  -- fully matched chains
    SELECT 'F_'||r, 1, 8 FROM generate_series(1,p_scale) r
    UNION ALL  -- right-side orphans: chain starts after join g (rows in g+1..8 only)
    SELECT 'O'||g||'_'||r, g + 1, 8
      FROM generate_series(1,7) g, generate_series(1,p_scale) r
    UNION ALL  -- bulk: mix of fully matched and random partial chains
    SELECT 'B'||g,
           CASE WHEN s < p_mismatch_pct THEN least(a,b)    ELSE 1 END,
           CASE WHEN s < p_mismatch_pct THEN greatest(a,b) ELSE 8 END
      FROM bulk
  )
  -- dense, collision-free keys; md5 ordering scatters matched/unmatched keys
  SELECT row_number() OVER (ORDER BY md5(id))::int AS k, lo, hi FROM raw;

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

  -- validity 2: every join edge also has a right-side orphan
  FOR jj IN 1..7 LOOP
    EXECUTE format('SELECT count(*) FROM oj_scale.%s WHERE NOT EXISTS (SELECT 1 FROM oj_scale.%s WHERE %s)',
                   (SELECT tab FROM oj_spec WHERE pos = jj + 1),
                   (SELECT tab FROM oj_spec WHERE pos = jj),
                   (SELECT on_cond FROM oj_spec WHERE pos = jj + 1)) INTO n;
    IF n = 0 THEN RAISE EXCEPTION 'join %: no right-side orphan', jj; END IF;
  END LOOP;
END $$;

-- ~10x base: 360 witness/full + 280 orphan + 12,000 bulk chains (~70% full, ~30% partial)
SELECT oj_scale.regen(12000, 10, 30);
ANALYZE;

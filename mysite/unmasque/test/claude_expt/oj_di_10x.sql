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

  INSERT INTO oj_scale.region   SELECT k, 

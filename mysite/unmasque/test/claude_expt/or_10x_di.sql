-- =====================================================================
-- Disjunction scaling, 10X data. Single table: part.
-- Query k:  SELECT * FROM part WHERE p_size IN (first k of 1,4,7,10,13,16,19,22,25,28)
-- Rows:
--   10 witness rows  : p_size = 1,4,7,...,28 (one row per IN value)
--   10000 filler rows : p_size = 1   -> in the result of EVERY query (result size does not depend on k)
--   1000 reject rows : p_size = 50  -> rejected by every query
-- Values are 3 apart, so they cannot collapse into a range.
-- Set the schema in config.ini to: disj_10x
-- =====================================================================
DROP SCHEMA IF EXISTS disj_10x CASCADE;
CREATE SCHEMA disj_10x;

CREATE TABLE disj_10x.part (
  p_partkey int PRIMARY KEY, p_name varchar(55) NOT NULL, p_mfgr char(25) NOT NULL,
  p_brand char(10) NOT NULL, p_type varchar(25) NOT NULL, p_size int NOT NULL,
  p_container char(10) NOT NULL, p_retailprice numeric(15,2) NOT NULL, p_comment varchar(23) NOT NULL);

-- witnesses: one row per disjunct value
INSERT INTO disj_10x.part
SELECT i, 'part' || i, 'M#1', 'Brand#1', 'T', 1 + 3 * (i - 1), 'SM BOX', 900.00, 'c'
FROM generate_series(1, 10) i;

-- fillers: satisfy every query
INSERT INTO disj_10x.part
SELECT 1000 + g, 'part' || (1000 + g), 'M#1', 'Brand#1', 'T', 1, 'SM BOX', 900.00, 'c'
FROM generate_series(1, 10000) g;

-- rejects: satisfy no query
INSERT INTO disj_10x.part
SELECT 900000 + g, 'part' || (900000 + g), 'M#1', 'Brand#1', 'T', 50, 'SM BOX', 900.00, 'c'
FROM generate_series(1, 1000) g;

-- validity: every IN value of every query has a witness, and every query rejects at least one row
DO $$
DECLARE vals int[] := ARRAY[1,4,7,10,13,16,19,22,25,28]; k int; i int; n bigint;
BEGIN
  FOR k IN 1..10 LOOP
    FOR i IN 1..k LOOP
      SELECT count(*) INTO n FROM disj_10x.part WHERE p_size = vals[i];
      IF n = 0 THEN RAISE EXCEPTION 'query %: value % has no witness', k, vals[i]; END IF;
    END LOOP;
    SELECT count(*) INTO n FROM disj_10x.part WHERE NOT (p_size = ANY (vals[1:k]));
    IF n = 0 THEN RAISE EXCEPTION 'query %: no rejected row', k; END IF;
  END LOOP;
END $$;

ANALYZE disj_10x.part;
SELECT count(*) AS total_rows FROM disj_10x.part;
-- cleanup: DROP SCHEMA disj_10x CASCADE;

-- Regenerate nep_scale.lineitem at 10X size (1,000 -> 10,000 filler rows).
-- The 11 witness/normal rows are re-inserted unchanged, so every NEP1..NEP10 query stays extractable.
-- Run in the same database where nep_scale was created. Change the argument to rescale (e.g. 100000 for 100X).

CREATE OR REPLACE FUNCTION nep_scale.regen(p_filler int) RETURNS void
LANGUAGE plpgsql AS $$
DECLARE kk int; ii int; n bigint;
BEGIN
  TRUNCATE nep_scale.lineitem;

  -- witnesses (one per NEP) + one row satisfying all NEPs
  INSERT INTO nep_scale.lineitem VALUES
   (101,1,1,1, 10,1000.00,0.02,0.02,'A','O','1994-03-10','1994-04-10','1994-05-10','NONE','TRUCK','c'),
   (1,1,1,1,   25,1000.00,0.02,0.02,'A','O','1994-03-10','1994-04-10','1994-05-10','NONE','TRUCK','c'),
   (2,1,1,1,   10,5000.00,0.02,0.02,'A','O','1994-03-10','1994-04-10','1994-05-10','NONE','TRUCK','c'),
   (3,1,1,1,   10,1000.00,0.05,0.02,'A','O','1994-03-10','1994-04-10','1994-05-10','NONE','TRUCK','c'),
   (4,1,1,1,   10,1000.00,0.02,0.04,'A','O','1994-03-10','1994-04-10','1994-05-10','NONE','TRUCK','c'),
   (5,1,1,1,   10,1000.00,0.02,0.02,'R','O','1994-03-10','1994-04-10','1994-05-10','NONE','TRUCK','c'),
   (6,1,1,1,   10,1000.00,0.02,0.02,'A','F','1994-03-10','1994-04-10','1994-05-10','NONE','TRUCK','c'),
   (7,1,1,1,   10,1000.00,0.02,0.02,'A','O','1994-03-10','1994-04-10','1994-05-10','COLLECT COD','TRUCK','c'),
   (8,1,1,1,   10,1000.00,0.02,0.02,'A','O','1994-03-10','1994-04-10','1994-05-10','NONE','AIR','c'),
   (9,1,1,1,   10,1000.00,0.02,0.02,'A','O','1995-06-15','1994-04-10','1994-05-10','NONE','TRUCK','c'),
   (10,1,1,1,  10,1000.00,0.02,0.02,'A','O','1994-03-10','1995-07-01','1994-05-10','NONE','TRUCK','c');

  -- filler rows: all satisfy every NEP
  INSERT INTO nep_scale.lineitem
  SELECT 1000 + g, 1, 1, 1, 10, 1000.00, 0.02, 0.02, 'A', 'O',
         DATE '1994-03-10', DATE '1994-04-10', DATE '1994-05-10', 'NONE', 'TRUCK', 'c'
  FROM generate_series(1, p_filler) g;

  -- validity check: each query returns rows, and each of its NEPs has a witness
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

SELECT nep_scale.regen(10000);          -- 10X: 10,011 rows (was 1,011)
ANALYZE nep_scale.lineitem;
SELECT count(*) AS total_rows FROM nep_scale.lineitem;

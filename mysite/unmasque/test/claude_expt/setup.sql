-- ============ helpers ============
CREATE OR REPLACE FUNCTION pm_base(s text, skip text[]) RETURNS void LANGUAGE plpgsql AS $$
BEGIN
  PERFORM prism_make_schema(s);
  EXECUTE format($f$
    INSERT INTO %1$I.region SELECT i,'REGION'||i,'c' FROM generate_series(0,4) i;
    INSERT INTO %1$I.nation SELECT i,'NATION'||i,i%%5,'c' FROM generate_series(0,24) i;
    INSERT INTO %1$I.part VALUES (900001,'p','M#1','Brand#1','T',1,'SM BOX',900,'c');
    INSERT INTO %1$I.partsupp VALUES (900001,900001,10,1,'c');
    INSERT INTO %1$I.lineitem VALUES (900001,900001,900001,1,1,100,0.05,0.02,'N','O',
      DATE '1995-01-02',DATE '1995-01-03',DATE '1995-01-04','NONE','AIR','c');
  $f$, s);
  -- neutral filler only in tables the query does NOT use
  IF NOT ('customer' = ANY(skip)) THEN EXECUTE format(
    'INSERT INTO %I.customer VALUES (900001,''c'',''a'',1,''20-000-000-0001'',100,''FURNITURE'',''c'')', s); END IF;
  IF NOT ('supplier' = ANY(skip)) THEN EXECUTE format(
    'INSERT INTO %I.supplier VALUES (900001,''s'',''a'',1,''10-000-000-0001'',100,''c'')', s); END IF;
  IF NOT ('orders' = ANY(skip)) THEN EXECUTE format(
    'INSERT INTO %I.orders VALUES (900001,900001,''O'',1000,DATE ''1995-01-01'',''3-MEDIUM'',''Clerk#1'',0,''c'')', s); END IF;
END $$;

CREATE OR REPLACE FUNCTION pm_c(s text, id int, seg text, bal numeric) RETURNS void LANGUAGE plpgsql AS $$
BEGIN EXECUTE format('INSERT INTO %I.customer VALUES (%s,%L,''a'',1,''20-000-000-0001'',%s,%L,''c'')',
  s, id, 'Customer#'||id, bal, seg); END $$;

CREATE OR REPLACE FUNCTION pm_s(s text, id int, bal numeric) RETURNS void LANGUAGE plpgsql AS $$
BEGIN EXECUTE format('INSERT INTO %I.supplier VALUES (%s,%L,''a'',1,''10-000-000-0001'',%s,''c'')',
  s, id, 'Supplier#'||id, bal); END $$;

CREATE OR REPLACE FUNCTION pm_o(s text, id int, cust int, st text, pr text, price numeric) RETURNS void LANGUAGE plpgsql AS $$
BEGIN EXECUTE format('INSERT INTO %I.orders VALUES (%s,%s,%L,%s,DATE ''1995-01-01'',%L,''Clerk#1'',0,''c'')',
  s, id, cust, st, price, pr); END $$;

-- ============ QN1: c_mktsegment <> 'BUILDING' AND c_acctbal > 9000 ============
SELECT pm_base('di_qn1_pos', ARRAY['customer']);
SELECT pm_c('di_qn1_pos', 1, 'BUILDING',   9500);   -- witness (violates <> only)
SELECT pm_c('di_qn1_pos', 2, 'AUTOMOBILE', 9500);   -- in QH result

SELECT pm_base('di_qn1_neg', ARRAY['customer']);    -- NO BUILDING witness
SELECT pm_c('di_qn1_neg', 2, 'AUTOMOBILE', 9500);
SELECT pm_c('di_qn1_neg', 3, 'FURNITURE',  9600);

-- ============ QN2: o_orderstatus <> 'F' AND o_orderpriority <> '1-URGENT' ============
SELECT pm_base('di_qn2_pos', ARRAY['orders']);
SELECT pm_o('di_qn2_pos', 1, 1, 'F', '2-HIGH',   1000);  -- violates NEP1 only
SELECT pm_o('di_qn2_pos', 2, 1, 'O', '1-URGENT', 1000);  -- violates NEP2 only
SELECT pm_o('di_qn2_pos', 3, 1, 'O', '2-HIGH',   1000);  -- in QH result

SELECT pm_base('di_qn2_negA', ARRAY['orders']);          -- only a double violator
SELECT pm_o('di_qn2_negA', 1, 1, 'F', '1-URGENT', 1000);
SELECT pm_o('di_qn2_negA', 3, 1, 'O', '2-HIGH',   1000);

SELECT pm_base('di_qn2_negB', ARRAY['orders']);          -- NEP2 witness missing
SELECT pm_o('di_qn2_negB', 1, 1, 'F', '2-HIGH', 1000);
SELECT pm_o('di_qn2_negB', 3, 1, 'O', '2-HIGH', 1000);

-- ============ QD1: c_mktsegment = 'BUILDING' OR c_acctbal > 9000 ============
SELECT pm_base('di_qd1_pos', ARRAY['customer']);
SELECT pm_c('di_qd1_pos', 1, 'BUILDING',   100);    -- only disjunct 1
SELECT pm_c('di_qd1_pos', 2, 'AUTOMOBILE', 9500);   -- only disjunct 2

SELECT pm_base('di_qd1_neg', ARRAY['customer']);    -- only rows satisfying both disjuncts
SELECT pm_c('di_qd1_neg', 1, 'BUILDING', 9500);
SELECT pm_c('di_qd1_neg', 2, 'BUILDING', 9600);

-- ============ QD2: segment IN (BUILDING, MACHINERY, AUTOMOBILE) AND c_acctbal > 5000 ============
SELECT pm_base('di_qd2_pos', ARRAY['customer']);
SELECT pm_c('di_qd2_pos', 1, 'BUILDING',   6000);
SELECT pm_c('di_qd2_pos', 2, 'MACHINERY',  6000);
SELECT pm_c('di_qd2_pos', 3, 'AUTOMOBILE', 6000);

SELECT pm_base('di_qd2_neg', ARRAY['customer']);    -- MACHINERY witness removed
SELECT pm_c('di_qd2_neg', 1, 'BUILDING',   6000);
SELECT pm_c('di_qd2_neg', 3, 'AUTOMOBILE', 6000);

-- ============ QU: customer UNION ALL supplier (each joined to nation, acctbal > 9000) ============
SELECT pm_base('di_qu_pos', ARRAY['customer','supplier']);
SELECT pm_c('di_qu_pos', 1, 'FURNITURE', 9500);
SELECT pm_s('di_qu_pos', 1, 9500);

SELECT pm_base('di_qu_neg', ARRAY['customer','supplier']);  -- supplier branch returns nothing
SELECT pm_c('di_qu_neg', 1, 'FURNITURE', 9500);
SELECT pm_s('di_qu_neg', 1, 100);

-- ============ QJ: customer LEFT OUTER JOIN orders ============
SELECT pm_base('di_qj_pos', ARRAY['customer','orders']);
SELECT pm_c('di_qj_pos', 1, 'BUILDING', 5000);
SELECT pm_c('di_qj_pos', 2, 'BUILDING', 6000);      -- unmatched (no order) -> NULL in result
SELECT pm_o('di_qj_pos', 10, 1, 'O', '3-MEDIUM', 1000);

SELECT pm_base('di_qj_neg', ARRAY['customer','orders']);    -- every customer matched
SELECT pm_c('di_qj_neg', 1, 'BUILDING', 5000);
SELECT pm_c('di_qj_neg', 2, 'BUILDING', 6000);
SELECT pm_o('di_qj_neg', 10, 1, 'O', '3-MEDIUM', 1000);
SELECT pm_o('di_qj_neg', 20, 2, 'O', '3-MEDIUM', 2000);

-- ============ sanity check: QH result on each D_I (optional) ============
SET search_path = di_qn1_pos, pg_catalog;
SELECT c_name, c_acctbal FROM customer WHERE c_mktsegment <> 'BUILDING' AND c_acctbal > 9000;
-- repeat per schema; reset with: SET search_path = public;

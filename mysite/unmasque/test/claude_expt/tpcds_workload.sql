-- =====================================================================
-- TPC-DS union scaling, 1X data. 16 TPC-DS tables (real table and column names, reduced column set), NO pk/fk constraints.
-- Chain key k = 1..1000: every table has one row per k and every surrogate-key column equals k, so every join matches.
-- Series: T3B3..T3B12 (3 branches) and T6B6..T6B12 (6 branches), see tpcds_workload.py
-- Join relations used (for your pk-fk file): fact.fk -> dimension.sk
--   store_sales.ss_store_sk -> store.s_store_sk, ss_hdemo_sk -> household_demographics.hd_demo_sk, ss_promo_sk -> promotion.p_promo_sk
--   catalog_sales.cs_catalog_page_sk -> catalog_page.cp_catalog_page_sk, cs_call_center_sk -> call_center.cc_call_center_sk, cs_ship_mode_sk -> ship_mode.sm_ship_mode_sk
--   web_sales.ws_web_site_sk -> web_site.web_site_sk, ws_web_page_sk -> web_page.wp_web_page_sk, ws_bill_addr_sk -> customer_address.ca_address_sk
--   store_returns.sr_reason_sk -> reason.r_reason_sk;  catalog_returns.cr_call_center_sk -> call_center.cc_call_center_sk;  web_returns.wr_web_page_sk -> web_page.wp_web_page_sk
-- Set the schema in config.ini to: tpcds_1x
-- =====================================================================
DROP SCHEMA IF EXISTS tpcds_1x CASCADE;
CREATE SCHEMA tpcds_1x;

CREATE TABLE tpcds_1x.store (s_store_sk int NOT NULL, s_store_id char(16) NOT NULL, s_store_name varchar(50) NOT NULL, s_number_employees int NOT NULL);
CREATE TABLE tpcds_1x.household_demographics (hd_demo_sk int NOT NULL, hd_income_band_sk int NOT NULL, hd_buy_potential char(15) NOT NULL, hd_dep_count int NOT NULL, hd_vehicle_count int NOT NULL);
CREATE TABLE tpcds_1x.promotion (p_promo_sk int NOT NULL, p_promo_id char(16) NOT NULL, p_promo_name char(50) NOT NULL, p_cost decimal(15,2) NOT NULL);
CREATE TABLE tpcds_1x.catalog_page (cp_catalog_page_sk int NOT NULL, cp_catalog_page_id char(16) NOT NULL, cp_description varchar(100) NOT NULL, cp_type varchar(100) NOT NULL);
CREATE TABLE tpcds_1x.call_center (cc_call_center_sk int NOT NULL, cc_call_center_id char(16) NOT NULL, cc_name varchar(50) NOT NULL, cc_employees int NOT NULL);
CREATE TABLE tpcds_1x.ship_mode (sm_ship_mode_sk int NOT NULL, sm_ship_mode_id char(16) NOT NULL, sm_type char(30) NOT NULL, sm_carrier char(20) NOT NULL);
CREATE TABLE tpcds_1x.web_site (web_site_sk int NOT NULL, web_site_id char(16) NOT NULL, web_name varchar(50) NOT NULL, web_class varchar(50) NOT NULL);
CREATE TABLE tpcds_1x.web_page (wp_web_page_sk int NOT NULL, wp_web_page_id char(16) NOT NULL, wp_url varchar(100) NOT NULL, wp_char_count int NOT NULL);
CREATE TABLE tpcds_1x.customer_address (ca_address_sk int NOT NULL, ca_address_id char(16) NOT NULL, ca_city varchar(60) NOT NULL, ca_state char(2) NOT NULL);
CREATE TABLE tpcds_1x.reason (r_reason_sk int NOT NULL, r_reason_id char(16) NOT NULL, r_reason_desc char(100) NOT NULL);
CREATE TABLE tpcds_1x.store_sales (ss_sold_date_sk int NOT NULL, ss_item_sk int NOT NULL, ss_customer_sk int NOT NULL, ss_hdemo_sk int NOT NULL, ss_store_sk int NOT NULL, ss_promo_sk int NOT NULL, ss_ticket_number int NOT NULL, ss_quantity int NOT NULL, ss_net_paid decimal(15,2) NOT NULL);
CREATE TABLE tpcds_1x.catalog_sales (cs_sold_date_sk int NOT NULL, cs_item_sk int NOT NULL, cs_bill_customer_sk int NOT NULL, cs_call_center_sk int NOT NULL, cs_catalog_page_sk int NOT NULL, cs_ship_mode_sk int NOT NULL, cs_order_number int NOT NULL, cs_quantity int NOT NULL, cs_net_paid decimal(15,2) NOT NULL);
CREATE TABLE tpcds_1x.web_sales (ws_sold_date_sk int NOT NULL, ws_item_sk int NOT NULL, ws_bill_customer_sk int NOT NULL, ws_bill_addr_sk int NOT NULL, ws_web_page_sk int NOT NULL, ws_web_site_sk int NOT NULL, ws_order_number int NOT NULL, ws_quantity int NOT NULL, ws_net_paid decimal(15,2) NOT NULL);
CREATE TABLE tpcds_1x.store_returns (sr_returned_date_sk int NOT NULL, sr_item_sk int NOT NULL, sr_customer_sk int NOT NULL, sr_store_sk int NOT NULL, sr_reason_sk int NOT NULL, sr_ticket_number int NOT NULL, sr_return_quantity int NOT NULL, sr_return_amt decimal(15,2) NOT NULL);
CREATE TABLE tpcds_1x.catalog_returns (cr_returned_date_sk int NOT NULL, cr_item_sk int NOT NULL, cr_refunded_customer_sk int NOT NULL, cr_call_center_sk int NOT NULL, cr_reason_sk int NOT NULL, cr_order_number int NOT NULL, cr_return_quantity int NOT NULL, cr_return_amount decimal(15,2) NOT NULL);
CREATE TABLE tpcds_1x.web_returns (wr_returned_date_sk int NOT NULL, wr_item_sk int NOT NULL, wr_refunded_customer_sk int NOT NULL, wr_web_page_sk int NOT NULL, wr_reason_sk int NOT NULL, wr_order_number int NOT NULL, wr_return_quantity int NOT NULL, wr_return_amt decimal(15,2) NOT NULL);

INSERT INTO tpcds_1x.store SELECT k, 'S' || lpad(k::text, 15, '0'), 'store' || k, 200 + k % 100 FROM generate_series(1, 1000) k;
INSERT INTO tpcds_1x.household_demographics SELECT k, k, '1001-5000', k % 10, k % 5 FROM generate_series(1, 1000) k;
INSERT INTO tpcds_1x.promotion SELECT k, 'P' || lpad(k::text, 15, '0'), 'promo' || k, 1000.00 FROM generate_series(1, 1000) k;
INSERT INTO tpcds_1x.catalog_page SELECT k, 'C' || lpad(k::text, 15, '0'), 'page' || k, 'monthly' FROM generate_series(1, 1000) k;
INSERT INTO tpcds_1x.call_center SELECT k, 'CC' || lpad(k::text, 14, '0'), 'center' || k, 100 + k % 50 FROM generate_series(1, 1000) k;
INSERT INTO tpcds_1x.ship_mode SELECT k, 'M' || lpad(k::text, 15, '0'), 'EXPRESS', 'UPS' FROM generate_series(1, 1000) k;
INSERT INTO tpcds_1x.web_site SELECT k, 'W' || lpad(k::text, 15, '0'), 'site' || k, 'Unknown' FROM generate_series(1, 1000) k;
INSERT INTO tpcds_1x.web_page SELECT k, 'WP' || lpad(k::text, 14, '0'), 'http://www.foo.com', 1000 + k % 500 FROM generate_series(1, 1000) k;
INSERT INTO tpcds_1x.customer_address SELECT k, 'A' || lpad(k::text, 15, '0'), 'city' || k, 'CA' FROM generate_series(1, 1000) k;
INSERT INTO tpcds_1x.reason SELECT k, 'R' || lpad(k::text, 15, '0'), 'reason' || k FROM generate_series(1, 1000) k;
INSERT INTO tpcds_1x.store_sales SELECT k, k, k, k, k, k, k, 1 + k % 100, 100 + k % 900 FROM generate_series(1, 1000) k;
INSERT INTO tpcds_1x.catalog_sales SELECT k, k, k, k, k, k, k, 1 + k % 100, 1000 + k % 900 FROM generate_series(1, 1000) k;
INSERT INTO tpcds_1x.web_sales SELECT k, k, k, k, k, k, k, 1 + k % 100, 2000 + k % 900 FROM generate_series(1, 1000) k;
INSERT INTO tpcds_1x.store_returns SELECT k, k, k, k, k, k, 1 + k % 50, 3000 + k % 900 FROM generate_series(1, 1000) k;
INSERT INTO tpcds_1x.catalog_returns SELECT k, k, k, k, k, k, 1 + k % 50, 4000 + k % 900 FROM generate_series(1, 1000) k;
INSERT INTO tpcds_1x.web_returns SELECT k, k, k, k, k, k, 1 + k % 50, 5000 + k % 900 FROM generate_series(1, 1000) k;

-- validity: every distinct branch used by the workload returns rows
DO $$
DECLARE b text; n bigint;
BEGIN
  PERFORM set_config('search_path', 'tpcds_1x, pg_catalog', true);
  FOREACH b IN ARRAY ARRAY[
    'SELECT ss_ticket_number, ss_net_paid FROM store_sales',
    'SELECT cs_order_number, cs_net_paid FROM catalog_sales',
    'SELECT ws_order_number, ws_net_paid FROM web_sales',
    'SELECT ss_ticket_number, ss_net_paid FROM store_sales, store WHERE ss_store_sk = s_store_sk',
    'SELECT cs_order_number, cs_net_paid FROM catalog_sales, catalog_page WHERE cs_catalog_page_sk = cp_catalog_page_sk',
    'SELECT ws_order_number, ws_net_paid FROM web_sales, web_site WHERE ws_web_site_sk = web_site_sk',
    'SELECT ss_ticket_number, ss_net_paid FROM store_sales, store, household_demographics WHERE ss_store_sk = s_store_sk AND ss_hdemo_sk = hd_demo_sk',
    'SELECT cs_order_number, cs_net_paid FROM catalog_sales, catalog_page, call_center WHERE cs_catalog_page_sk = cp_catalog_page_sk AND cs_call_center_sk = cc_call_center_sk',
    'SELECT ws_order_number, ws_net_paid FROM web_sales, web_site, web_page WHERE ws_web_site_sk = web_site_sk AND ws_web_page_sk = wp_web_page_sk',
    'SELECT ss_ticket_number, ss_net_paid FROM store_sales, store, household_demographics, promotion WHERE ss_store_sk = s_store_sk AND ss_hdemo_sk = hd_demo_sk AND ss_promo_sk = p_promo_sk',
    'SELECT cs_order_number, cs_net_paid FROM catalog_sales, catalog_page, call_center, ship_mode WHERE cs_catalog_page_sk = cp_catalog_page_sk AND cs_call_center_sk = cc_call_center_sk AND cs_ship_mode_sk = sm_ship_mode_sk',
    'SELECT ws_order_number, ws_net_paid FROM web_sales, web_site, web_page, customer_address WHERE ws_web_site_sk = web_site_sk AND ws_web_page_sk = wp_web_page_sk AND ws_bill_addr_sk = ca_address_sk',
    'SELECT sr_ticket_number, sr_return_amt FROM store_returns',
    'SELECT cr_order_number, cr_return_amount FROM catalog_returns',
    'SELECT wr_order_number, wr_return_amt FROM web_returns',
    'SELECT sr_ticket_number, sr_return_amt FROM store_returns, reason WHERE sr_reason_sk = r_reason_sk',
    'SELECT cr_order_number, cr_return_amount FROM catalog_returns, call_center WHERE cr_call_center_sk = cc_call_center_sk',
    'SELECT wr_order_number, wr_return_amt FROM web_returns, web_page WHERE wr_web_page_sk = wp_web_page_sk'] LOOP
    EXECUTE 'SELECT count(*) FROM (' || b || ') q' INTO n;
    IF n = 0 THEN RAISE EXCEPTION 'branch returns no rows: %', b; END IF;
  END LOOP;
END $$;

ANALYZE;
-- expected: 0 primary keys, 0 foreign keys
SELECT count(*) FILTER (WHERE contype = 'p') AS primary_keys, count(*) FILTER (WHERE contype = 'f') AS foreign_keys
FROM pg_constraint WHERE connamespace = 'tpcds_1x'::regnamespace;
-- cleanup: DROP SCHEMA tpcds_1x CASCADE;

-- =====================================================================
-- TPC-DS union scaling, 10X data. 16 TPC-DS tables (real table and column names, reduced column set), NO pk/fk constraints.
-- Chain key k = 1..10000: every table has one row per k and every surrogate-key column equals k, so every join matches.
-- Series: T3B3..T3B12 (3 branches) and T6B6..T6B12 (6 branches), see tpcds_workload.py
-- Join relations used (for your pk-fk file): fact.fk -> dimension.sk
--   store_sales.ss_store_sk -> store.s_store_sk, ss_hdemo_sk -> household_demographics.hd_demo_sk, ss_promo_sk -> promotion.p_promo_sk
--   catalog_sales.cs_catalog_page_sk -> catalog_page.cp_catalog_page_sk, cs_call_center_sk -> call_center.cc_call_center_sk, cs_ship_mode_sk -> ship_mode.sm_ship_mode_sk
--   web_sales.ws_web_site_sk -> web_site.web_site_sk, ws_web_page_sk -> web_page.wp_web_page_sk, ws_bill_addr_sk -> customer_address.ca_address_sk
--   store_returns.sr_reason_sk -> reason.r_reason_sk;  catalog_returns.cr_call_center_sk -> call_center.cc_call_center_sk;  web_returns.wr_web_page_sk -> web_page.wp_web_page_sk
-- Set the schema in config.ini to: tpcds_10x
-- =====================================================================
DROP SCHEMA IF EXISTS tpcds_10x CASCADE;
CREATE SCHEMA tpcds_10x;

CREATE TABLE tpcds_10x.store (s_store_sk int NOT NULL, s_store_id char(16) NOT NULL, s_store_name varchar(50) NOT NULL, s_number_employees int NOT NULL);
CREATE TABLE tpcds_10x.household_demographics (hd_demo_sk int NOT NULL, hd_income_band_sk int NOT NULL, hd_buy_potential char(15) NOT NULL, hd_dep_count int NOT NULL, hd_vehicle_count int NOT NULL);
CREATE TABLE tpcds_10x.promotion (p_promo_sk int NOT NULL, p_promo_id char(16) NOT NULL, p_promo_name char(50) NOT NULL, p_cost decimal(15,2) NOT NULL);
CREATE TABLE tpcds_10x.catalog_page (cp_catalog_page_sk int NOT NULL, cp_catalog_page_id char(16) NOT NULL, cp_description varchar(100) NOT NULL, cp_type varchar(100) NOT NULL);
CREATE TABLE tpcds_10x.call_center (cc_call_center_sk int NOT NULL, cc_call_center_id char(16) NOT NULL, cc_name varchar(50) NOT NULL, cc_employees int NOT NULL);
CREATE TABLE tpcds_10x.ship_mode (sm_ship_mode_sk int NOT NULL, sm_ship_mode_id char(16) NOT NULL, sm_type char(30) NOT NULL, sm_carrier char(20) NOT NULL);
CREATE TABLE tpcds_10x.web_site (web_site_sk int NOT NULL, web_site_id char(16) NOT NULL, web_name varchar(50) NOT NULL, web_class varchar(50) NOT NULL);
CREATE TABLE tpcds_10x.web_page (wp_web_page_sk int NOT NULL, wp_web_page_id char(16) NOT NULL, wp_url varchar(100) NOT NULL, wp_char_count int NOT NULL);
CREATE TABLE tpcds_10x.customer_address (ca_address_sk int NOT NULL, ca_address_id char(16) NOT NULL, ca_city varchar(60) NOT NULL, ca_state char(2) NOT NULL);
CREATE TABLE tpcds_10x.reason (r_reason_sk int NOT NULL, r_reason_id char(16) NOT NULL, r_reason_desc char(100) NOT NULL);
CREATE TABLE tpcds_10x.store_sales (ss_sold_date_sk int NOT NULL, ss_item_sk int NOT NULL, ss_customer_sk int NOT NULL, ss_hdemo_sk int NOT NULL, ss_store_sk int NOT NULL, ss_promo_sk int NOT NULL, ss_ticket_number int NOT NULL, ss_quantity int NOT NULL, ss_net_paid decimal(15,2) NOT NULL);
CREATE TABLE tpcds_10x.catalog_sales (cs_sold_date_sk int NOT NULL, cs_item_sk int NOT NULL, cs_bill_customer_sk int NOT NULL, cs_call_center_sk int NOT NULL, cs_catalog_page_sk int NOT NULL, cs_ship_mode_sk int NOT NULL, cs_order_number int NOT NULL, cs_quantity int NOT NULL, cs_net_paid decimal(15,2) NOT NULL);
CREATE TABLE tpcds_10x.web_sales (ws_sold_date_sk int NOT NULL, ws_item_sk int NOT NULL, ws_bill_customer_sk int NOT NULL, ws_bill_addr_sk int NOT NULL, ws_web_page_sk int NOT NULL, ws_web_site_sk int NOT NULL, ws_order_number int NOT NULL, ws_quantity int NOT NULL, ws_net_paid decimal(15,2) NOT NULL);
CREATE TABLE tpcds_10x.store_returns (sr_returned_date_sk int NOT NULL, sr_item_sk int NOT NULL, sr_customer_sk int NOT NULL, sr_store_sk int NOT NULL, sr_reason_sk int NOT NULL, sr_ticket_number int NOT NULL, sr_return_quantity int NOT NULL, sr_return_amt decimal(15,2) NOT NULL);
CREATE TABLE tpcds_10x.catalog_returns (cr_returned_date_sk int NOT NULL, cr_item_sk int NOT NULL, cr_refunded_customer_sk int NOT NULL, cr_call_center_sk int NOT NULL, cr_reason_sk int NOT NULL, cr_order_number int NOT NULL, cr_return_quantity int NOT NULL, cr_return_amount decimal(15,2) NOT NULL);
CREATE TABLE tpcds_10x.web_returns (wr_returned_date_sk int NOT NULL, wr_item_sk int NOT NULL, wr_refunded_customer_sk int NOT NULL, wr_web_page_sk int NOT NULL, wr_reason_sk int NOT NULL, wr_order_number int NOT NULL, wr_return_quantity int NOT NULL, wr_return_amt decimal(15,2) NOT NULL);

INSERT INTO tpcds_10x.store SELECT k, 'S' || lpad(k::text, 15, '0'), 'store' || k, 200 + k % 100 FROM generate_series(1, 10000) k;
INSERT INTO tpcds_10x.household_demographics SELECT k, k, '1001-5000', k % 10, k % 5 FROM generate_series(1, 10000) k;
INSERT INTO tpcds_10x.promotion SELECT k, 'P' || lpad(k::text, 15, '0'), 'promo' || k, 1000.00 FROM generate_series(1, 10000) k;
INSERT INTO tpcds_10x.catalog_page SELECT k, 'C' || lpad(k::text, 15, '0'), 'page' || k, 'monthly' FROM generate_series(1, 10000) k;
INSERT INTO tpcds_10x.call_center SELECT k, 'CC' || lpad(k::text, 14, '0'), 'center' || k, 100 + k % 50 FROM generate_series(1, 10000) k;
INSERT INTO tpcds_10x.ship_mode SELECT k, 'M' || lpad(k::text, 15, '0'), 'EXPRESS', 'UPS' FROM generate_series(1, 10000) k;
INSERT INTO tpcds_10x.web_site SELECT k, 'W' || lpad(k::text, 15, '0'), 'site' || k, 'Unknown' FROM generate_series(1, 10000) k;
INSERT INTO tpcds_10x.web_page SELECT k, 'WP' || lpad(k::text, 14, '0'), 'http://www.foo.com', 1000 + k % 500 FROM generate_series(1, 10000) k;
INSERT INTO tpcds_10x.customer_address SELECT k, 'A' || lpad(k::text, 15, '0'), 'city' || k, 'CA' FROM generate_series(1, 10000) k;
INSERT INTO tpcds_10x.reason SELECT k, 'R' || lpad(k::text, 15, '0'), 'reason' || k FROM generate_series(1, 10000) k;
INSERT INTO tpcds_10x.store_sales SELECT k, k, k, k, k, k, k, 1 + k % 100, 100 + k % 900 FROM generate_series(1, 10000) k;
INSERT INTO tpcds_10x.catalog_sales SELECT k, k, k, k, k, k, k, 1 + k % 100, 1000 + k % 900 FROM generate_series(1, 10000) k;
INSERT INTO tpcds_10x.web_sales SELECT k, k, k, k, k, k, k, 1 + k % 100, 2000 + k % 900 FROM generate_series(1, 10000) k;
INSERT INTO tpcds_10x.store_returns SELECT k, k, k, k, k, k, 1 + k % 50, 3000 + k % 900 FROM generate_series(1, 10000) k;
INSERT INTO tpcds_10x.catalog_returns SELECT k, k, k, k, k, k, 1 + k % 50, 4000 + k % 900 FROM generate_series(1, 10000) k;
INSERT INTO tpcds_10x.web_returns SELECT k, k, k, k, k, k, 1 + k % 50, 5000 + k % 900 FROM generate_series(1, 10000) k;

-- validity: every distinct branch used by the workload returns rows
DO $$
DECLARE b text; n bigint;
BEGIN
  PERFORM set_config('search_path', 'tpcds_10x, pg_catalog', true);
  FOREACH b IN ARRAY ARRAY[
    'SELECT ss_ticket_number, ss_net_paid FROM store_sales',
    'SELECT cs_order_number, cs_net_paid FROM catalog_sales',
    'SELECT ws_order_number, ws_net_paid FROM web_sales',
    'SELECT ss_ticket_number, ss_net_paid FROM store_sales, store WHERE ss_store_sk = s_store_sk',
    'SELECT cs_order_number, cs_net_paid FROM catalog_sales, catalog_page WHERE cs_catalog_page_sk = cp_catalog_page_sk',
    'SELECT ws_order_number, ws_net_paid FROM web_sales, web_site WHERE ws_web_site_sk = web_site_sk',
    'SELECT ss_ticket_number, ss_net_paid FROM store_sales, store, household_demographics WHERE ss_store_sk = s_store_sk AND ss_hdemo_sk = hd_demo_sk',
    'SELECT cs_order_number, cs_net_paid FROM catalog_sales, catalog_page, call_center WHERE cs_catalog_page_sk = cp_catalog_page_sk AND cs_call_center_sk = cc_call_center_sk',
    'SELECT ws_order_number, ws_net_paid FROM web_sales, web_site, web_page WHERE ws_web_site_sk = web_site_sk AND ws_web_page_sk = wp_web_page_sk',
    'SELECT ss_ticket_number, ss_net_paid FROM store_sales, store, household_demographics, promotion WHERE ss_store_sk = s_store_sk AND ss_hdemo_sk = hd_demo_sk AND ss_promo_sk = p_promo_sk',
    'SELECT cs_order_number, cs_net_paid FROM catalog_sales, catalog_page, call_center, ship_mode WHERE cs_catalog_page_sk = cp_catalog_page_sk AND cs_call_center_sk = cc_call_center_sk AND cs_ship_mode_sk = sm_ship_mode_sk',
    'SELECT ws_order_number, ws_net_paid FROM web_sales, web_site, web_page, customer_address WHERE ws_web_site_sk = web_site_sk AND ws_web_page_sk = wp_web_page_sk AND ws_bill_addr_sk = ca_address_sk',
    'SELECT sr_ticket_number, sr_return_amt FROM store_returns',
    'SELECT cr_order_number, cr_return_amount FROM catalog_returns',
    'SELECT wr_order_number, wr_return_amt FROM web_returns',
    'SELECT sr_ticket_number, sr_return_amt FROM store_returns, reason WHERE sr_reason_sk = r_reason_sk',
    'SELECT cr_order_number, cr_return_amount FROM catalog_returns, call_center WHERE cr_call_center_sk = cc_call_center_sk',
    'SELECT wr_order_number, wr_return_amt FROM web_returns, web_page WHERE wr_web_page_sk = wp_web_page_sk'] LOOP
    EXECUTE 'SELECT count(*) FROM (' || b || ') q' INTO n;
    IF n = 0 THEN RAISE EXCEPTION 'branch returns no rows: %', b; END IF;
  END LOOP;
END $$;

ANALYZE;
-- expected: 0 primary keys, 0 foreign keys
SELECT count(*) FILTER (WHERE contype = 'p') AS primary_keys, count(*) FILTER (WHERE contype = 'f') AS foreign_keys
FROM pg_constraint WHERE connamespace = 'tpcds_10x'::regnamespace;
-- cleanup: DROP SCHEMA tpcds_10x CASCADE;

# Query results

Queries and saved run outcomes from `tests-examples/prism-pilots` and `results/prism-pilot`.

This catalog covers **13 query IDs and 48 saved runs**. Original NEP2 and NEP3 have no saved runs in this collection; their reduced variants, NEP2_a and NEP3_a, are included under separate IDs. Original NEP1 was attempted and was killed after running out of memory, but its saved record was not supplied. That attempt is noted here and excluded from the 48-run total.

**IDs with saved results:** DS1, DS2, DS3, NEP1_a, NEP2_a, NEP3_a, OJ1, OJ2, OJ3, UK3, UK_a, UN3, UN_a.

Queries below reproduce the SQL in each ID's `taskw.yaml`. Run labels come from the saved filenames: parallel uses `cubes.py`; sequential uses `sequential.py`; taskw/taskwo refer to the respective task YAML. All saved runs are run1.

Timings are copied exactly from the saved files: real = elapsed wall time, user = user CPU time, sys = system CPU time. CPU time can exceed elapsed time for parallel runs. Manual stops are not automatic timeouts or proof that no solution exists. For UN3 and UN_a, taskwo was not run separately because it is identical to taskw. These are not additional measured runs.

Outcomes beginning “Solution emitted” are inferred from the SQL Solution section in raw logs and do not establish equivalence on arbitrary data. Other outcomes and assessments are copied from the saved result summaries. These tables preserve the observations recorded in the logs. The final correctness classifications are in [correctness_review.md](correctness_review.md); those classifications are used for the plots. No queries were rerun when preparing this catalog.

## DS1

Query source: [tests-examples/prism-pilots/DS1/taskw.yaml](../tests-examples/prism-pilots/DS1/taskw.yaml).

```sql
SELECT p_partkey, p_name, p_comment
FROM part
WHERE p_container IN ('SM CASE');
```

| Mode | Task | Run | real | user | sys | Outcome | Saved file |
| --- | --- | --- | --- | --- | --- | --- | --- |
| parallel | taskw | 1 | 0m1.856s | 0m3.703s | 0m1.433s | Solution emitted (R and SQL); general equivalence not assessed | [parallel_taskw_run1.log](prism-pilot/DS1_res/parallel_taskw_run1.log) |
| parallel | taskwo | 1 | 0m1.838s | 0m4.582s | 0m1.536s | Solution emitted (R and SQL); general equivalence not assessed | [parallel_taskwo_run1.log](prism-pilot/DS1_res/parallel_taskwo_run1.log) |
| sequential | taskw | 1 | 0m1.789s | 0m2.164s | 0m0.994s | Solution emitted (R and SQL); general equivalence not assessed | [sequential_taskw_run1.log](prism-pilot/DS1_res/sequential_taskw_run1.log) |
| sequential | taskwo | 1 | 0m40.889s | 0m41.155s | 0m0.903s | Solution emitted (R and SQL); general equivalence not assessed | [sequential_taskwo_run1.log](prism-pilot/DS1_res/sequential_taskwo_run1.log) |

- **taskwo runs:** Both saved candidates use ordering and a row limit (`head`/`LIMIT`) rather than the target container predicate. A returned candidate alone does not prove recovery of the intended query.

## DS2

Query source: [tests-examples/prism-pilots/DS2/taskw.yaml](../tests-examples/prism-pilots/DS2/taskw.yaml).

```sql
SELECT p_partkey, p_name, p_comment
FROM part
WHERE p_container IN ('SM CASE', 'SM BOX');
```

| Mode | Task | Run | real | user | sys | Outcome | Saved file |
| --- | --- | --- | --- | --- | --- | --- | --- |
| parallel | taskw | 1 | 0m1.827s | 0m3.824s | 0m1.360s | Solution emitted (R and SQL); general equivalence not assessed | [parallel_taskw_run1.log](prism-pilot/DS2_res/parallel_taskw_run1.log) |
| parallel | taskwo | 1 | 0m1.919s | 0m4.504s | 0m1.645s | Solution emitted (R and SQL); general equivalence not assessed | [parallel_taskwo_run1.log](prism-pilot/DS2_res/parallel_taskwo_run1.log) |
| sequential | taskw | 1 | 0m2.465s | 0m2.863s | 0m1.068s | Solution emitted (R and SQL); general equivalence not assessed | [sequential_taskw_run1.log](prism-pilot/DS2_res/sequential_taskw_run1.log) |
| sequential | taskwo | 1 | 0m40.826s | 0m41.229s | 0m0.892s | Solution emitted (R and SQL); general equivalence not assessed | [sequential_taskwo_run1.log](prism-pilot/DS2_res/sequential_taskwo_run1.log) |

- **taskwo runs:** Both saved candidates use ordering and a row limit (`head`/`LIMIT`) rather than the target container predicate. A returned candidate alone does not prove recovery of the intended query.

## DS3

Query source: [tests-examples/prism-pilots/DS3/taskw.yaml](../tests-examples/prism-pilots/DS3/taskw.yaml).

```sql
SELECT p_partkey, p_name, p_comment
FROM part
WHERE p_container IN ('SM CASE', 'SM BOX', 'SM PACK');
```

| Mode | Task | Run | real | user | sys | Outcome | Saved file |
| --- | --- | --- | --- | --- | --- | --- | --- |
| parallel | taskw | 1 | 0m7.042s | 0m57.424s | 0m1.745s | Solution emitted (R and SQL); general equivalence not assessed | [parallel_taskw_run1.log](prism-pilot/DS3_res/parallel_taskw_run1.log) |
| parallel | taskwo | 1 | 0m1.891s | 0m4.600s | 0m1.438s | Solution emitted (R and SQL); general equivalence not assessed | [parallel_taskwo_run1.log](prism-pilot/DS3_res/parallel_taskwo_run1.log) |
| sequential | taskw | 1 | 0m15.323s | 0m15.705s | 0m1.026s | Solution emitted (R and SQL); general equivalence not assessed | [sequential_taskw_run1.log](prism-pilot/DS3_res/sequential_taskw_run1.log) |
| sequential | taskwo | 1 | 0m40.826s | 0m41.222s | 0m1.073s | Solution emitted (R and SQL); general equivalence not assessed | [sequential_taskwo_run1.log](prism-pilot/DS3_res/sequential_taskwo_run1.log) |

- **taskwo runs:** Both saved candidates use ordering and a row limit (`head`/`LIMIT`) rather than the target container predicate. A returned candidate alone does not prove recovery of the intended query.
- **taskw runs:** Saved candidates use multiple filters and joins rather than the literal target IN predicate; the raw logs contain no general-equivalence assessment.

## NEP1_a

Query source: [tests-examples/prism-pilots/NEP1_a/taskw.yaml](../tests-examples/prism-pilots/NEP1_a/taskw.yaml).

```sql
SELECT l_orderkey
FROM lineitem
WHERE l_quantity <> 25;
```

| Mode | Task | Run | real | user | sys | Outcome | Saved file |
| --- | --- | --- | --- | --- | --- | --- | --- |
| parallel | taskw | 1 | 0m1.753s | 0m3.127s | 0m1.296s | Solution found; intended filter and projection recovered | [parallel_taskw_run1.txt](prism-pilot/NEP1_a_res/parallel_taskw_run1.txt) |
| parallel | taskwo | 1 | 10m24.294s | 103m55.872s | 0m6.766s | Manually terminated with Ctrl+C; no solution returned | [parallel_taskwo_run1.txt](prism-pilot/NEP1_a_res/parallel_taskwo_run1.txt) |
| sequential | taskw | 1 | 0m2.076s | 0m2.266s | 0m1.065s | Solution found; intended filter and projection recovered | [sequential_taskw_run1.txt](prism-pilot/NEP1_a_res/sequential_taskw_run1.txt) |
| sequential | taskwo | 1 | 9m48.189s | 9m48.832s | 0m1.290s | Manually terminated with Ctrl+C; no solution returned | [sequential_taskwo_run1.txt](prism-pilot/NEP1_a_res/sequential_taskwo_run1.txt) |

## NEP2_a

Query source: [tests-examples/prism-pilots/NEP2_a/taskw.yaml](../tests-examples/prism-pilots/NEP2_a/taskw.yaml).

```sql
SELECT l_orderkey
FROM lineitem
WHERE l_quantity <> 25
  AND l_extendedprice <> 5000.00;
```

| Mode | Task | Run | real | user | sys | Outcome | Saved file |
| --- | --- | --- | --- | --- | --- | --- | --- |
| parallel | taskw | 1 | 0m3.266s | 0m17.511s | 0m1.602s | Candidate matches the example but is not generally equivalent to the target | [parallel_taskw_run1.txt](prism-pilot/NEP2_a_res/parallel_taskw_run1.txt) |
| parallel | taskwo | 1 | 22m8.161s | 221m15.741s | 0m9.277s | Manually terminated with Ctrl+C; no solution returned | [parallel_taskwo_run1.txt](prism-pilot/NEP2_a_res/parallel_taskwo_run1.txt) |
| sequential | taskw | 1 | 0m4.717s | 0m5.098s | 0m1.073s | Solution found; intended filter and projection recovered | [sequential_taskw_run1.txt](prism-pilot/NEP2_a_res/sequential_taskw_run1.txt) |
| sequential | taskwo | 1 | 7m39.206s | 7m39.698s | 0m1.162s | Manually terminated with Ctrl+C; no solution returned | [sequential_taskwo_run1.txt](prism-pilot/NEP2_a_res/sequential_taskwo_run1.txt) |

- **parallel/taskw:** Difference: Uses l_extendedprice > 5000 instead of l_extendedprice != 5000.
- **parallel/taskw:** Counterexample: A row with l_quantity = 10 and l_extendedprice = 4000 satisfies the target but not the candidate.

## NEP3_a

Query source: [tests-examples/prism-pilots/NEP3_a/taskw.yaml](../tests-examples/prism-pilots/NEP3_a/taskw.yaml).

```sql
SELECT l_orderkey
FROM lineitem
WHERE l_quantity <> 25
  AND l_extendedprice <> 5000.00
  AND l_discount <> 0.05;
```

| Mode | Task | Run | real | user | sys | Outcome | Saved file |
| --- | --- | --- | --- | --- | --- | --- | --- |
| parallel | taskw | 1 | 2m20.569s | 23m8.587s | 0m4.550s | Candidate matches the example but is not generally equivalent to the target | [parallel_taskw_run1.txt](prism-pilot/NEP3_a_res/parallel_taskw_run1.txt) |
| parallel | taskwo | 1 | 5m5.233s | 50m39.646s | 0m3.715s | Manually terminated with Ctrl+C; no solution returned | [parallel_taskwo_run1.txt](prism-pilot/NEP3_a_res/parallel_taskwo_run1.txt) |
| sequential | taskw | 1 | 2m25.949s | 2m25.910s | 0m1.610s | Candidate matches the example but is not generally equivalent to the target | [sequential_taskw_run1.txt](prism-pilot/NEP3_a_res/sequential_taskw_run1.txt) |
| sequential | taskwo | 1 | 13m0.042s | 13m0.403s | 0m1.276s | Manually terminated with Ctrl+C; no solution returned | [sequential_taskwo_run1.txt](prism-pilot/NEP3_a_res/sequential_taskwo_run1.txt) |

- **parallel/taskw:** Differences: Uses different predicates and ORDER BY l_discount with LIMIT 2.
- **parallel/taskw:** The target has no row limit and can return more than two qualifying rows.
- **sequential/taskw:** Differences: Uses price > 5000 instead of price != 5000; adds an OR condition.
- **sequential/taskw:** Counterexample: Quantity 10, price 4000, discount 0.07 satisfies the target but is excluded by the candidate.

## OJ1

Query source: [tests-examples/prism-pilots/OJ1/taskw.yaml](../tests-examples/prism-pilots/OJ1/taskw.yaml).

```sql
SELECT r_name, n_name
FROM region
LEFT OUTER JOIN nation ON r_regionkey = n_regionkey;
```

| Mode | Task | Run | real | user | sys | Outcome | Saved file |
| --- | --- | --- | --- | --- | --- | --- | --- |
| parallel | taskw | 1 | 0m29.455s | 4m38.714s | 0m2.159s | Solution emitted (R and SQL); general equivalence not assessed | [parallel_taskw_run1.log](prism-pilot/OJ1_res/parallel_taskw_run1.log) |
| parallel | taskwo | 1 | 0m3.701s | 0m21.897s | 0m1.660s | Solution emitted (R and SQL); general equivalence not assessed | [parallel_taskwo_run1.log](prism-pilot/OJ1_res/parallel_taskwo_run1.log) |
| sequential | taskw | 1 | 11m18.597s | 11m19.169s | 0m1.207s | Manually terminated with Ctrl+C; no solution returned | [sequential_taskw_run1.txt](prism-pilot/OJ1_res/sequential_taskw_run1.txt) |
| sequential | taskwo | 1 | 0m11.652s | 0m12.019s | 0m1.164s | Solution emitted (R and SQL); general equivalence not assessed | [sequential_taskwo_run1.log](prism-pilot/OJ1_res/sequential_taskwo_run1.log) |

## OJ2

Query source: [tests-examples/prism-pilots/OJ2/taskw.yaml](../tests-examples/prism-pilots/OJ2/taskw.yaml).

```sql
SELECT r_name, n_name, s_name
FROM region
LEFT OUTER JOIN nation ON r_regionkey = n_regionkey
LEFT OUTER JOIN supplier ON n_nationkey = s_nationkey;
```

| Mode | Task | Run | real | user | sys | Outcome | Saved file |
| --- | --- | --- | --- | --- | --- | --- | --- |
| parallel | taskw | 1 | 14m55.533s | 148m54.728s | 0m11.323s | Manually terminated with Ctrl+C; no solution returned | [parallel_taskw_run1.txt](prism-pilot/OJ2_res/parallel_taskw_run1.txt) |
| parallel | taskwo | 1 | 11m43.622s | 116m34.849s | 0m4.227s | Manually terminated with Ctrl+C; no solution returned | [parallel_taskwo_run1.txt](prism-pilot/OJ2_res/parallel_taskwo_run1.txt) |
| sequential | taskw | 1 | 7m22.576s | 7m22.789s | 0m1.548s | Manually terminated with Ctrl+C; no solution returned | [sequential_taskw_run1.txt](prism-pilot/OJ2_res/sequential_taskw_run1.txt) |
| sequential | taskwo | 1 | 8m32.499s | 8m32.896s | 0m1.055s | Manually terminated with Ctrl+C; no solution returned | [sequential_taskwo_run1.txt](prism-pilot/OJ2_res/sequential_taskwo_run1.txt) |

## OJ3

Query source: [tests-examples/prism-pilots/OJ3/taskw.yaml](../tests-examples/prism-pilots/OJ3/taskw.yaml).

```sql
SELECT r_name, n_name, s_name, ps_availqty
FROM region
LEFT OUTER JOIN nation ON r_regionkey = n_regionkey
LEFT OUTER JOIN supplier ON n_nationkey = s_nationkey
LEFT OUTER JOIN partsupp ON s_suppkey = ps_suppkey;
```

| Mode | Task | Run | real | user | sys | Outcome | Saved file |
| --- | --- | --- | --- | --- | --- | --- | --- |
| parallel | taskw | 1 | 12m54.164s | 128m41.416s | 0m8.235s | Manually terminated with Ctrl+C; no solution returned | [parallel_taskw_run1.txt](prism-pilot/OJ3_res/parallel_taskw_run1.txt) |
| parallel | taskwo | 1 | 8m22.242s | 83m27.767s | 0m4.205s | Manually terminated with Ctrl+C; no solution returned | [parallel_taskwo_run1.txt](prism-pilot/OJ3_res/parallel_taskwo_run1.txt) |
| sequential | taskw | 1 | 7m22.764s | 7m23.009s | 0m1.278s | Manually terminated with Ctrl+C; no solution returned | [sequential_taskw_run1.txt](prism-pilot/OJ3_res/sequential_taskw_run1.txt) |
| sequential | taskwo | 1 | 6m20.585s | 6m20.842s | 0m1.179s | Manually terminated with Ctrl+C; no solution returned | [sequential_taskwo_run1.txt](prism-pilot/OJ3_res/sequential_taskwo_run1.txt) |

## UK3

Query source: [tests-examples/prism-pilots/UK3/taskw.yaml](../tests-examples/prism-pilots/UK3/taskw.yaml).

```sql
(SELECT r_name, r_regionkey FROM region, nation, supplier WHERE r_regionkey = n_regionkey AND n_nationkey = s_nationkey)
UNION ALL
(SELECT ps_comment, ps_supplycost FROM partsupp, part, lineitem WHERE ps_partkey = p_partkey AND p_partkey = l_partkey)
UNION ALL
(SELECT o_clerk, o_totalprice FROM orders, customer WHERE o_custkey = c_custkey);
```

| Mode | Task | Run | real | user | sys | Outcome | Saved file |
| --- | --- | --- | --- | --- | --- | --- | --- |
| parallel | taskw | 1 | 6m46.752s | 67m0.821s | 0m34.377s | Manually terminated with Ctrl+C; no solution returned | [parallel_taskw_run1.txt](prism-pilot/UK3_res/parallel_taskw_run1.txt) |
| parallel | taskwo | 1 | 6m48.925s | 67m21.975s | 0m32.503s | Manually terminated with Ctrl+C; no solution returned | [parallel_taskwo_run1.txt](prism-pilot/UK3_res/parallel_taskwo_run1.txt) |
| sequential | taskw | 1 | 4m14.201s | 4m11.071s | 0m4.653s | Manually terminated with Ctrl+C; no solution returned | [sequential_taskw_run1.txt](prism-pilot/UK3_res/sequential_taskw_run1.txt) |
| sequential | taskwo | 1 | 5m58.886s | 5m53.472s | 0m6.952s | Manually terminated with Ctrl+C; no solution returned | [sequential_taskwo_run1.txt](prism-pilot/UK3_res/sequential_taskwo_run1.txt) |

## UK_a

Query source: [tests-examples/prism-pilots/UK_a/taskw.yaml](../tests-examples/prism-pilots/UK_a/taskw.yaml).

```sql
SELECT n_name
FROM nation
INNER JOIN supplier ON n_nationkey = s_nationkey
UNION ALL
SELECT n_name
FROM nation
INNER JOIN customer ON n_nationkey = c_nationkey;
```

| Mode | Task | Run | real | user | sys | Outcome | Saved file |
| --- | --- | --- | --- | --- | --- | --- | --- |
| parallel | taskw | 1 | 0m33.782s | 5m24.727s | 0m2.073s | R solution found; SQL generation failed | [parallel_taskw_run1.txt](prism-pilot/UK_a_res/parallel_taskw_run1.txt) |
| parallel | taskwo | 1 | 3m57.732s | 39m25.943s | 0m3.312s | Manually terminated with Ctrl+C; no solution returned | [parallel_taskwo_run1.txt](prism-pilot/UK_a_res/parallel_taskwo_run1.txt) |
| sequential | taskw | 1 | 9m56.092s | 9m56.507s | 0m1.620s | Manually terminated with Ctrl+C; no solution returned | [sequential_taskw_run1.txt](prism-pilot/UK_a_res/sequential_taskw_run1.txt) |
| sequential | taskwo | 1 | 9m35.245s | 9m26.987s | 0m10.315s | Manually terminated with Ctrl+C; no solution returned | [sequential_taskwo_run1.txt](prism-pilot/UK_a_res/sequential_taskwo_run1.txt) |

- **parallel/taskw:** Assessment: Generated R joins nation with customer and supplier separately, combines the results using bind_rows, and projects n_name. This implements the target UNION ALL operation.
- **SQL conversion failure:** The saved error is “Argument 1 must be a data frame or a named atomic vector.” No SQL query was generated for the affected runs.

## UN3

Query source: [tests-examples/prism-pilots/UN3/taskw.yaml](../tests-examples/prism-pilots/UN3/taskw.yaml).

```sql
(SELECT s_name, s_acctbal FROM supplier)
UNION ALL
(SELECT c_name, c_acctbal FROM customer)
UNION ALL
(SELECT p_name, p_retailprice FROM part);
```

| Mode | Task | Run | real | user | sys | Outcome | Saved file |
| --- | --- | --- | --- | --- | --- | --- | --- |
| parallel | taskw | 1 | 5m49.131s | 57m59.823s | 0m3.387s | Manually terminated with Ctrl+C; no solution returned | [parallel_taskw_run1.txt](prism-pilot/UN3_res/parallel_taskw_run1.txt) |
| sequential | taskw | 1 | 6m17.936s | 6m17.825s | 0m1.126s | Manually terminated with Ctrl+C; no solution returned | [sequential_taskw_run1.txt](prism-pilot/UN3_res/sequential_taskw_run1.txt) |

- **Not run separately:** parallel/taskwo and sequential/taskwo use the same YAML configuration as taskw.

## UN_a

Query source: [tests-examples/prism-pilots/UN_a/taskw.yaml](../tests-examples/prism-pilots/UN_a/taskw.yaml).

```sql
SELECT name FROM supplier_names
UNION ALL
SELECT name FROM customer_names;
```

| Mode | Task | Run | real | user | sys | Outcome | Saved file |
| --- | --- | --- | --- | --- | --- | --- | --- |
| parallel | taskw | 1 | 0m1.796s | 0m3.207s | 0m1.407s | R solution found; SQL generation failed | [parallel_taskw_run1.txt](prism-pilot/UN_a_res/parallel_taskw_run1.txt) |
| sequential | taskw | 1 | 0m1.765s | 0m2.204s | 0m1.059s | R solution found; SQL generation failed | [sequential_taskw_run1.txt](prism-pilot/UN_a_res/sequential_taskw_run1.txt) |

- **parallel/taskw:** Patch applied: No
- **sequential/taskw:** Patch applied: No
- **SQL conversion failure:** The saved error is “Argument 1 must be a data frame or a named atomic vector.” No SQL query was generated for the affected runs.
- **Not run separately:** parallel/taskwo and sequential/taskwo use the same YAML configuration as taskw.

## Outcome counts

| Saved outcome category | Runs |
| --- | ---: |
| R and SQL solution emitted; general equivalence not assessed | 15 |
| Intended filter and projection reported recovered | 3 |
| Manually terminated; no solution returned | 24 |
| Candidate reported non-equivalent to target | 3 |
| R solution found; SQL generation failed | 3 |
| Total | 48 |

# Review of CUBES results

This review covers 48 saved runs across 13 query IDs. The real, user, and system times for all runs agree with the summary, giving 144 matching timing values. All 21 generated SQL queries return the expected rows on the supplied examples, including duplicate counts. To distinguish correct queries from ones that only fit those examples, the queries were also checked by examining their operations and running additional SQLite counterexamples.

| Outcome | Runs |
| --- | ---: |
| Correct under TPC-H constraints | 11 |
| Incorrect | 10 |
| Manually stopped | 24 |
| R solution found; SQL conversion failed | 3 |

A query is marked correct when it is equivalent to the target under the TPC-H schema constraints. The DS3 sequential run with hints assumes that p_partkey is unique and p_name and p_container are not NULL. The OJ1 results assume a unique r_regionkey and non-NULL r_name. These conclusions may not hold for arbitrary CSVs that violate those constraints. Output row order is ignored.

Three runs found R solutions but failed to generate SQL. Their R programs were inspected and represent the intended union operations, but they were not executed again during this review. These runs are recorded separately from incorrect SQL and manually stopped searches. No CUBES experiments were rerun, and no CUBES code or packages were changed during the review.

| Query | Mode | Task | Real seconds | Classification |
| --- | --- | --- | ---: | --- |
| DS1 | parallel | taskw | 1.856 | Correct under TPC-H constraints |
| DS1 | parallel | taskwo | 1.838 | Incorrect |
| DS1 | sequential | taskw | 1.789 | Correct under TPC-H constraints |
| DS1 | sequential | taskwo | 40.889 | Incorrect |
| DS2 | parallel | taskw | 1.827 | Correct under TPC-H constraints |
| DS2 | parallel | taskwo | 1.919 | Incorrect |
| DS2 | sequential | taskw | 2.465 | Correct under TPC-H constraints |
| DS2 | sequential | taskwo | 40.826 | Incorrect |
| DS3 | parallel | taskw | 7.042 | Incorrect |
| DS3 | parallel | taskwo | 1.891 | Incorrect |
| DS3 | sequential | taskw | 15.323 | Correct under TPC-H constraints |
| DS3 | sequential | taskwo | 40.826 | Incorrect |
| NEP1_a | parallel | taskw | 1.753 | Correct under TPC-H constraints |
| NEP1_a | parallel | taskwo | 624.294 | Manually stopped |
| NEP1_a | sequential | taskw | 2.076 | Correct under TPC-H constraints |
| NEP1_a | sequential | taskwo | 588.189 | Manually stopped |
| NEP2_a | parallel | taskw | 3.266 | Incorrect |
| NEP2_a | parallel | taskwo | 1328.161 | Manually stopped |
| NEP2_a | sequential | taskw | 4.717 | Correct under TPC-H constraints |
| NEP2_a | sequential | taskwo | 459.206 | Manually stopped |
| NEP3_a | parallel | taskw | 140.569 | Incorrect |
| NEP3_a | parallel | taskwo | 305.233 | Manually stopped |
| NEP3_a | sequential | taskw | 145.949 | Incorrect |
| NEP3_a | sequential | taskwo | 780.042 | Manually stopped |
| OJ1 | parallel | taskw | 29.455 | Correct under TPC-H constraints |
| OJ1 | parallel | taskwo | 3.701 | Correct under TPC-H constraints |
| OJ1 | sequential | taskw | 678.597 | Manually stopped |
| OJ1 | sequential | taskwo | 11.652 | Correct under TPC-H constraints |
| OJ2 | parallel | taskw | 895.533 | Manually stopped |
| OJ2 | parallel | taskwo | 703.622 | Manually stopped |
| OJ2 | sequential | taskw | 442.576 | Manually stopped |
| OJ2 | sequential | taskwo | 512.499 | Manually stopped |
| OJ3 | parallel | taskw | 774.164 | Manually stopped |
| OJ3 | parallel | taskwo | 502.242 | Manually stopped |
| OJ3 | sequential | taskw | 442.764 | Manually stopped |
| OJ3 | sequential | taskwo | 380.585 | Manually stopped |
| UK3 | parallel | taskw | 406.752 | Manually stopped |
| UK3 | parallel | taskwo | 408.925 | Manually stopped |
| UK3 | sequential | taskw | 254.201 | Manually stopped |
| UK3 | sequential | taskwo | 358.886 | Manually stopped |
| UK_a | parallel | taskw | 33.782 | R solution found; SQL conversion failed |
| UK_a | parallel | taskwo | 237.732 | Manually stopped |
| UK_a | sequential | taskw | 596.092 | Manually stopped |
| UK_a | sequential | taskwo | 575.245 | Manually stopped |
| UN3 | parallel | taskw | 349.131 | Manually stopped |
| UN3 | sequential | taskw | 377.936 | Manually stopped |
| UN_a | parallel | taskw | 1.796 | R solution found; SQL conversion failed |
| UN_a | sequential | taskw | 1.765 | R solution found; SQL conversion failed |

## Additional checks

- DS1/parallel/taskwo: Six qualifying parts: the target returns six; the candidate LIMIT truncates the result. Rows returned: target 6, candidate 2.
- DS1/sequential/taskwo: Six qualifying parts: the target returns six; the candidate LIMIT truncates the result. Rows returned: target 6, candidate 2.
- DS2/parallel/taskwo: Six qualifying parts: the target returns six; the candidate LIMIT truncates the result. Rows returned: target 6, candidate 3.
- DS2/sequential/taskwo: Six qualifying parts: the target returns six; the candidate LIMIT truncates the result. Rows returned: target 6, candidate 3.
- DS3/parallel/taskw: One qualifying part and no excluded containers: target returns one; candidate cross joins an empty RHS and returns zero. Rows returned: target 1, candidate 0.
- DS3/parallel/taskwo: Six qualifying parts: the target returns six; the candidate LIMIT truncates the result. Rows returned: target 6, candidate 4.
- DS3/sequential/taskwo: Six qualifying parts: the target returns six; the candidate LIMIT truncates the result. Rows returned: target 6, candidate 4.
- NEP2_a/parallel/taskw: Quantity 10, price 4000, discount 0.07: target includes this row; candidate price > 5000 excludes it. Rows returned: target 1, candidate 0.
- NEP3_a/parallel/taskw: Quantity 10, price 5000, discount 0.01: target excludes this row; candidate includes it. Rows returned: target 0, candidate 1.
- NEP3_a/sequential/taskw: Quantity 10, price 4000, discount 0.07: target includes this row; candidate price > 5000 excludes it. Rows returned: target 1, candidate 0.

## Coverage notes

- UN3 and UN_a were tested only with taskw because taskwo contains the same configuration. They are not counted as separate measurements.
- The original NEP1 run was killed after running out of memory. Its saved result file was not supplied, so it is not included in these 48 runs.
- Some TXT files are manually recorded run summaries. Their timings were checked against those files; they were not measured again.
- A manually stopped run means that no solution had been returned when Ctrl+C was pressed. It does not prove that no solution exists. Stopping times differ between runs.

- The plots use real elapsed time, including startup and SQL conversion. Each configuration has one measured run; the figures do not show averages. SQL conversion failures and manually stopped runs have separate labels.

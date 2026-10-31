# Extractable Query Class:
---------------------------------------------------------------------------------------

query      ::= flat | branch (union_op branch)+
branch     ::= "(" flat ")"
union_op   ::= UNION ALL

flat       ::= SELECT list(item) FROM source
               [WHERE condition] [GROUP BY list(column)]
               [ORDER BY list(order_item)] [LIMIT int]

item       ::= expression [AS identifier]
expression ::= scalar | aggregate "(" scalar ")" | COUNT(*)
aggregate  ::= SUM | AVG | MIN | MAX | COUNT
scalar     ::= column | constant | "(" scalar ")"
             | scalar arithmetic scalar
arithmetic ::= "+" | "-" | "*" | "/"

source     ::= list(table) | table (join_op table ON condition)+
join_op    ::= JOIN | INNER JOIN | LEFT OUTER JOIN
             | RIGHT OUTER JOIN | FULL OUTER JOIN

condition  ::= conjunct (AND conjunct)*
conjunct   ::= atom (OR atom)* | column IN "(" list(constant) ")"
             | column <> constant | column NOT LIKE string
atom       ::= column comparison (column | constant)
             | column LIKE string
comparison ::= "=" | "<" | "<=" | ">" | ">="

order_item ::= (identifier | column) [ASC | DESC]
column     ::= identifier ["." identifier]
constant   ::= number | date | string

------------------------------------------------------------------------------

## Observability Conditions

The conditions under which PRISM can deterministically extract a hidden query `Q_H` from an initial database `D_I`, in a single list. Each item is tagged with the construct it applies to.

1. **[General]** `D_I` is NULL-free (if it is not, a NULL-free sample can be constructed from it).
2. **[General]** `Q_H` produces a populated result on `D_I`. When outer joins or unions are present, the result must be a fully instantiated result (FIT-result), i.e., it contains at least one tuple with no NULL values.
3. **[General]** No table is repeated in the `FROM` clause of `Q_H` (no self-joins).
4. **[General]** `Q_H` is conjunctive, extended to a conjunction of clauses where each clause is a disjunction of atomic predicates.
5. **[General]** `Q_H` is not a pure count query.
6. **[Union]** Each subquery `q_i` independently produces a FIT-result on `D_I`.
7. **[Union]** Each subquery `q_i` is not a pure count query.
8. **[Union]** For `i ≠ j`, `AUX(q_i)` is not a subset of `AUX(q_j)`, where `AUX(q_i)` is the set of tables of `q_i` that do not occur in every subquery (the non-containment condition).
9. **[Algebraic predicates (ALP)]** No condition beyond the general ones.
10. **[Negation (NEP)]** For each negation predicate `col <> val` in `Q_H`, `D_I` contains at least one tuple with `col = val`.
11. **[Disjunction]** For each disjunct `p_i^j` of each clause `c_j`, `D_I` contains a witness tuple that satisfies `p_i^j` and every other clause `c_l` (`l ≠ j`), but falsifies all other disjuncts of `c_j`.
12. **[Outer joins]** The projection of `Q_H` contains at least one non-aggregated attribute from every participating relation, so that the NULL-extended side of an outer join is visible in the result.

Remark: `HAVING` clause support is added within the flat-scope. It is not integrated with the new features present in `PRISM`.

# Setting up the PRISM Code:
-------------------------------------------------------------------------------------------------------------------------------------------------

# Setting Up the Database
## PostgreSQL Installation  

Follow the link https://www.postgresql.org/download/ to download and install the suitable distribution of the database for your platform. 

## Loading TPCH Data  

### Obtaining DBGEN
1. Open the TPC webpage following the link: https://www.tpc.org/tpc_documents_current_versions/current_specifications5.asp  
2. In the `Active Benchmarks` table (first table), follow the link of `Download TPC-H_Tools_v3.0.1.zip`, it'll redirect to `TPC-H Tools Download
` page   
3. Give your details and click `download`, it'll email you the download link. Use the link to download the zip file.  
4. Unzip the zip file, and it must have the `dbgen` folder among the extracted contents  

### Prepare TPCH data on PostgreSQL using DBGEN
1. Download the code `tpch-pgsql` from the link: [https://github.com/Data-Science-Platform/tpch-pgsql/tree/master](https://github.com/ahanapradhan/tpch-pgsql).  
2. Follow the `tpch-pgsql` project Readme to prepare and load the data.  
3. (In case the above command gives error as `malloc.h` not found, showing the filenames, go inside dbgen folder, open the file and replace `malloc.h` with `stdlib.h`)

## Sample TPCH Data  
TPCH 100MB (sf=0.1) data is provided at: https://github.com/ahanapradhan/UnionExtraction/blob/master/mysite/unmasque/test/experiments/data/tpch_tiny.zip  
The load.sql file in the folder needs to be updated with the corresponding location of the data .csv files.

## Loading TPCH Data using DuckDB
https://duckdb.org/docs/extensions/tpch.html

# Setting up IDE
A developement environment for python project is required next. Here is the link to PyCharm Community Edition: https://www.jetbrains.com/pycharm/download/  (Any other IDE is also fine)

### Requirements
* Python 3.8.0 or above
* `django==4.2.4`
* `sympy==1.4`
* `psycopg2==2.9.3`
* `numpy==1.22.4`

# Setting Up the Code

The code is organized into the following directories:  

## mysite

The `mysite` directory contains the main project code.

### unmasque

Inside `unmasque`, you'll find the following subdirectories:

#### src

The `src` directory contains code `PRISM` code: which is `unmasque` core extended with the notion of FIT-ness, and the full implementation of PRISM extractors.
#### test

(obsolete) The `test` directory houses unit test cases for each extractor module. These tests are crucial for ensuring the reliability and correctness of the code.

Please explore the individual directories for more details on the code and its purpose.

# Usage

## Configuration
inside `mysite` directory, there are two files as follows:  
pkfkrelations.csv --> contains key details for the TPCH schema. If any other schema is to be used, change this file accordingly.
config.ini --> This contains database login credentials and flags for optional features. Change the fields accordingly.  

### Config File Details:
`database` section: set your database credentials.  

`support` section: give support file name. The support file should be present in the same directory of this config file.

`logging` section: set logging level. The developer mode is `DEBUG`. Other valid levels are `INFO`, `ERROR`.

`feature` section: set flags for advanced features, as the flag names indicate. Included features are, `UNION`, `OUTER JOIN`, `<>` or `!=` operator in arithmetic filter predicates and `IN` operator. 

`options` section: extractor options. E.g. the maximum value for `LIMIT` clause is 1000. If the user needs to set a higher value, use `limit=value`.


### Running PRISM
Open `mysite/unmasque/src/main_cmd.py` file.  
This script has one default input specified.  
Change this query to try PRISM for various inputs.  
`test.util` package has `queries.py` file, containing a few sample queries. Any of them can be used for testing.

#### From Command Line:
Change the current directory to `mysite`.
Use the following command:  
`python -m unmasque.src.main_cmd` 

#### From IDE:
the `main` function in main_cmd.py can be run from the IDE.  


(Current code uses relative imports in main_cmd.py script. If that causes import related error while trying to run from IDE, please change the imports to absolute.)

#### From GUI:
In the terminal, go inside `unmasque` folder and start the Django app using the command: `python3 manage.py runserver`
Once the server is up at the 8080 port of localhost, the GUI can be accessed through the link: `http://localhost:8080/unmasque/`




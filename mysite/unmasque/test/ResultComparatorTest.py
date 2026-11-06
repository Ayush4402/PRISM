import unittest

from mysite.unmasque.src.core.result_comparator import ResultComparator


class _FakeLogger:
    def isEnabledFor(self, level):
        return False

    def debug(self, *args, **kwargs):
        pass


class _FakeConfig:
    schema = "fresh"
    user_schema = "public"
    database = "postgres"


class _FakeQueries:
    def hashtext_query(self, alias, table):
        return f"hashtext({alias})"


class _FakeConnection:
    def __init__(self):
        self.config = _FakeConfig()
        self.queries = _FakeQueries()
        self.sql = []
        self.fetchone_queries = []
        self.fetchone_result = (1, 2)

    def execute_sql(self, queries, logger=None):
        self.sql.append(queries)

    def execute_sql_fetchone(self, query):
        self.fetchone_queries.append(query)
        return self.fetchone_result


def _bare_result_comparator(is_hash=True, database="postgres"):
    comparator = object.__new__(ResultComparator)
    comparator.isHash = is_hash
    comparator.logger = _FakeLogger()
    comparator.r_e = "re_E"
    comparator.r_h = "rh_E"
    comparator.connectionHelper = _FakeConnection()
    comparator.connectionHelper.config.database = database
    return comparator


class IsMatchTest(unittest.TestCase):
    def test_hash_match_on_equal_non_none_lengths(self):
        comparator = _bare_result_comparator()
        created = []
        comparator._create_working_schema = lambda: created.append(True)

        self.assertTrue(comparator.is_match(4, 4))
        self.assertEqual([True], created)

    def test_hash_mismatch_does_not_create_schema(self):
        comparator = _bare_result_comparator()
        created = []
        comparator._create_working_schema = lambda: created.append(True)

        self.assertFalse(comparator.is_match(4, 5))
        self.assertFalse(comparator.is_match(None, None))
        self.assertEqual([], created)

    def test_non_hash_match_uses_base_rule(self):
        comparator = _bare_result_comparator(is_hash=False)
        created = []
        comparator._create_working_schema = lambda: created.append(True)

        self.assertTrue(comparator.is_match(0, 0))
        self.assertEqual([True], created)

    def test_non_hash_mismatch_does_not_create_schema(self):
        comparator = _bare_result_comparator(is_hash=False)
        created = []
        comparator._create_working_schema = lambda: created.append(True)

        self.assertFalse(comparator.is_match(3, 0))
        self.assertEqual([], created)


class HashDiffQueryTest(unittest.TestCase):
    def test_postgres_combines_both_hashes_in_one_query(self):
        comparator = _bare_result_comparator()
        comparator.connectionHelper.fetchone_result = (7, 7)

        left, right = comparator.run_hash_diff_queries()

        self.assertEqual((7, 7), (left, right))
        self.assertEqual(["select (hashtext(re_E)), (hashtext(rh_E));"],
                         comparator.connectionHelper.fetchone_queries)

    def test_oracle_appends_from_dual(self):
        comparator = _bare_result_comparator(database="oracle")

        comparator.run_hash_diff_queries()

        self.assertEqual(["select (hashtext(re_E)), (hashtext(rh_E)) from dual;"],
                         comparator.connectionHelper.fetchone_queries)

    def test_no_row_returns_none_pair(self):
        comparator = _bare_result_comparator()
        comparator.connectionHelper.fetchone_result = None

        self.assertEqual((None, None), comparator.run_hash_diff_queries())


class InsertDataIntoQhTableTest(unittest.TestCase):
    def test_batches_at_class_batch_size(self):
        comparator = _bare_result_comparator()
        rows = [("id", "value")] + [(i, i + 1) for i in range(ResultComparator.INSERT_BATCH_SIZE + 1)]

        comparator.insert_data_into_Qh_table(rows, "qh")

        self.assertEqual(2, len(comparator.connectionHelper.sql))
        self.assertTrue(comparator.connectionHelper.sql[0][0].startswith("INSERT INTO fresh.qh(id, value) VALUES"))
        self.assertTrue(comparator.connectionHelper.sql[0][0].endswith(";"))
        self.assertNotIn("), (", comparator.connectionHelper.sql[1][0])

    def test_only_all_null_rows_are_skipped(self):
        comparator = _bare_result_comparator()
        rows = [("a", "b"), ("None", "None"), (None, None), (1, 2)]

        comparator.insert_data_into_Qh_table(rows, "qh")

        self.assertEqual(1, len(comparator.connectionHelper.sql))
        self.assertIn("VALUES ('1', '2');", comparator.connectionHelper.sql[0][0])

    def test_python_none_is_rendered_as_string_none(self):
        comparator = _bare_result_comparator()

        comparator.insert_data_into_Qh_table([("a", "b"), (None, "x")], "qh")

        self.assertEqual(1, len(comparator.connectionHelper.sql))
        self.assertIn("VALUES ('None', 'x');", comparator.connectionHelper.sql[0][0])

    def test_none_literal_in_partial_row_becomes_sql_null(self):
        comparator = _bare_result_comparator()

        comparator.insert_data_into_Qh_table([("a", "b"), ("None", "x")], "qh")

        self.assertEqual(1, len(comparator.connectionHelper.sql))
        self.assertIn("VALUES (NULL, 'x');", comparator.connectionHelper.sql[0][0])

    def test_all_none_literal_row_is_skipped(self):
        comparator = _bare_result_comparator()

        comparator.insert_data_into_Qh_table([("a", "b"), ("None", "None")], "qh")

        self.assertEqual([], comparator.connectionHelper.sql)

    def test_single_cell_result_is_wrapped(self):
        comparator = _bare_result_comparator()

        comparator.insert_data_into_Qh_table([("c",), ("abc",)], "qh")

        self.assertEqual(1, len(comparator.connectionHelper.sql))
        self.assertIn("INSERT INTO fresh.qh(c) VALUES ('abc');", comparator.connectionHelper.sql[0][0])

    def test_single_cell_result_already_parenthesized_is_not_wrapped_twice(self):
        comparator = _bare_result_comparator()

        comparator.insert_data_into_Qh_table([("c",), ("(abc)",)], "qh")

        self.assertIn("VALUES (abc);", comparator.connectionHelper.sql[0][0])

    def test_header_only_result_inserts_nothing(self):
        comparator = _bare_result_comparator()

        comparator.insert_data_into_Qh_table([("a", "b")], "qh")

        self.assertEqual([], comparator.connectionHelper.sql)


if __name__ == "__main__":
    unittest.main()

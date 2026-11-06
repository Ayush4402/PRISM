import unittest

from mysite.unmasque.src.core.nep import NEP, NepComparator


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
    def update_key_attrib_with_val(self, table, attrib, value, prev, quoted):
        suffix = "q" if quoted else "n"
        return f"{table}.{attrib}={value}({prev}){suffix}"


class _FakeConnection:
    def __init__(self):
        self.config = _FakeConfig()
        self.queries = _FakeQueries()
        self.sql = []

    def execute_sql(self, queries, logger=None):
        self.sql.append(queries)


def _bare_nep_comparator():
    comparator = object.__new__(NepComparator)
    comparator.logger = _FakeLogger()
    comparator.connectionHelper = _FakeConnection()
    return comparator


def _bare_nep():
    nep = object.__new__(NEP)
    nep.logger = _FakeLogger()
    nep.connectionHelper = _FakeConnection()
    return nep


class _FakeApp:
    def __init__(self, result=None, empty=True):
        self.result = result
        self.empty = empty
        self.calls = 0

    def doJob(self, query):
        self.calls += 1
        return self.result

    def isQ_result_empty(self, result):
        return self.empty


class InsertDataIntoQhTableTest(unittest.TestCase):
    def test_batches_at_class_batch_size(self):
        comparator = _bare_nep_comparator()
        rows = [("id", "value")] + [(i, i + 1) for i in range(NepComparator.INSERT_BATCH_SIZE + 1)]

        comparator.insert_data_into_Qh_table(rows, "qh")

        self.assertEqual(2, len(comparator.connectionHelper.sql))
        self.assertTrue(comparator.connectionHelper.sql[0][0].startswith("INSERT INTO fresh.qh(id, value) VALUES"))
        self.assertTrue(comparator.connectionHelper.sql[0][0].endswith(";"))
        self.assertNotIn("), (", comparator.connectionHelper.sql[1][0])

    def test_any_null_row_is_skipped(self):
        comparator = _bare_nep_comparator()
        rows = [("a", "b"), (None, "x"), ("y", "None"), ("p", None), (1, 2)]

        comparator.insert_data_into_Qh_table(rows, "qh")

        self.assertEqual(1, len(comparator.connectionHelper.sql))
        self.assertIn("VALUES (1, 2);", comparator.connectionHelper.sql[0][0])

    def test_none_literal_is_skipped(self):
        comparator = _bare_nep_comparator()
        comparator.insert_data_into_Qh_table([("a",), ("None",)], "qh")

        self.assertEqual([], comparator.connectionHelper.sql)

    def test_multi_cell_literal_null_is_rendered_as_sql_null(self):
        comparator = _bare_nep_comparator()
        comparator.insert_data_into_Qh_table([("a", "b"), ("x", "NULL")], "qh")

        self.assertEqual(1, len(comparator.connectionHelper.sql))
        self.assertIn("VALUES ('x', NULL);", comparator.connectionHelper.sql[0][0])

    def test_single_cell_result_is_wrapped(self):
        comparator = _bare_nep_comparator()
        comparator.insert_data_into_Qh_table([("c",), ("abc",)], "qh")

        self.assertEqual(1, len(comparator.connectionHelper.sql))
        self.assertIn("INSERT INTO fresh.qh(c) VALUES ('abc');", comparator.connectionHelper.sql[0][0])

    def test_single_cell_result_already_parenthesized_is_not_wrapped_twice(self):
        comparator = _bare_nep_comparator()
        comparator.insert_data_into_Qh_table([("c",), ("(abc)",)], "qh")

        self.assertIn("VALUES (abc);", comparator.connectionHelper.sql[0][0])

    def test_header_only_result_inserts_nothing(self):
        comparator = _bare_nep_comparator()

        comparator.insert_data_into_Qh_table([("a", "b")], "qh")

        self.assertEqual([], comparator.connectionHelper.sql)


class NepActualJobTest(unittest.TestCase):
    def test_app_query_runs_once_and_result_is_shared(self):
        nep = _bare_nep()
        result = [("row",)]
        nep.app = _FakeApp(result=result)
        seen = []

        def extract_NEP_for_table(tabname, query, is_for_joined, res=None):
            seen.append((tabname, query, is_for_joined, res))
            return [("nonkey",)] if not is_for_joined else [("key",)]

        nep.extract_NEP_for_table = extract_NEP_for_table

        filters = nep.doActualJob((("select 1", "t1"),))

        self.assertEqual([("nonkey",), ("key",)], filters)
        self.assertEqual(1, nep.app.calls)
        self.assertEqual(2, len(seen))
        self.assertEqual((result, result), (seen[0][3], seen[1][3]))
        self.assertEqual([False, True], [entry[2] for entry in seen])


class ExtractNepForTableTest(unittest.TestCase):
    def test_empty_result_checks_attribs_with_supplied_result(self):
        nep = _bare_nep()
        nep.app = _FakeApp(result=[], empty=True)
        nep.global_all_attribs = {"t1": ["a", "b"]}
        nep.joined_attribs = None
        calls = []
        nep._NEP__check_per_attrib = (
            lambda attrib_list, tabname, query, filter_attribs, is_for_joined:
            filter_attribs + [(tabname, is_for_joined)]
        )

        filters = nep.extract_NEP_for_table("t1", "select 1", False, res=[])

        self.assertEqual([("t1", False)], filters)
        self.assertEqual(0, nep.app.calls)

    def test_result_is_fetched_when_not_supplied(self):
        nep = _bare_nep()
        nep.app = _FakeApp(result=[], empty=True)
        nep.global_all_attribs = {"t1": ["a"]}
        nep.joined_attribs = None
        nep._NEP__check_per_attrib = (
            lambda attrib_list, tabname, query, filter_attribs, is_for_joined: filter_attribs
        )

        nep.extract_NEP_for_table("t1", "select 1", False)

        self.assertEqual(1, nep.app.calls)

    def test_non_empty_result_does_not_check_attribs(self):
        nep = _bare_nep()
        nep.app = _FakeApp(result=[("x",)], empty=False)
        nep.global_all_attribs = {"t1": ["a"]}
        nep.joined_attribs = None

        filters = nep.extract_NEP_for_table("t1", "select 1", False, res=[("x",)])

        self.assertEqual([], filters)


class UpdateKeyAttribWithValTest(unittest.TestCase):
    def test_updates_are_executed_in_one_batch(self):
        nep = _bare_nep()
        nep.get_datatype = lambda key: "int" if key[1] == "a" else "char"

        nep._NEP__update_key_attib_with_val(["t1", "t2"], ["a", "b"], 5, 1)

        self.assertEqual(1, len(nep.connectionHelper.sql))
        self.assertEqual(
            ["fresh.t1.a=5(1)n", "fresh.t2.b=5(1)q"],
            nep.connectionHelper.sql[0],
        )


if __name__ == "__main__":
    unittest.main()

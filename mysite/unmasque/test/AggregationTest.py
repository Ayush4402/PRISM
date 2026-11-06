import unittest

from mysite.unmasque.src.core.aggregation import (
    Aggregation,
    get_k_value,
    get_k_value_for_number,
    get_no_of_rows,
)
from mysite.unmasque.src.util.constants import AVG, COUNT, MAX, MIN, SUM


class _FakeLogger:
    def isEnabledFor(self, level):
        return False

    def debug(self, *args, **kwargs):
        pass


def _bare_aggregation():
    agg = object.__new__(Aggregation)
    agg.logger = _FakeLogger()
    agg.core_relations = ["t1", "t2"]
    agg.global_all_attribs = {"t1": ["a", "b"], "t2": ["c", "d"]}
    agg.filter_attrib_dict = {}
    agg.dependencies = [[("t1", "a")]]
    agg.get_datatype = lambda key: "int"
    return agg


class KValueTest(unittest.TestCase):
    def test_equal_values_non_two(self):
        k_value, agg_array = get_k_value_for_number(3, 3)
        self.assertEqual(1, k_value)
        self.assertEqual([SUM, 6, AVG, 3, MIN, 3, MAX, 3, COUNT, 2], agg_array)

    def test_equal_values_two(self):
        k_value, agg_array = get_k_value_for_number(2, 2)
        self.assertEqual(2, k_value)
        self.assertEqual([SUM, 6, AVG, 2, MIN, 2, MAX, 2, COUNT, 3], agg_array)

    def test_distinct_values_skip_constrained_k(self):
        k_value, agg_array = get_k_value_for_number(2, 5)
        self.assertEqual(3, k_value)
        self.assertEqual([SUM, 11, AVG, 2.75, MIN, 2, MAX, 5, COUNT, 4], agg_array)

    def test_groupby_key_number_ignores_filters(self):
        a, agg_array, b, k_value = get_k_value("x", {("t", "x"): (100, 200)}, True, "t", "int", 0)
        self.assertEqual((3, 3), (a, b))
        self.assertEqual(1, k_value)
        self.assertEqual([SUM, 6, AVG, 3, MIN, 3, MAX, 3, COUNT, 2], agg_array)

    def test_number_filter(self):
        a, agg_array, b, k_value = get_k_value("x", {("t", "x"): (0, 10)}, False, "t", "int", 0)
        self.assertEqual((1, 0), (a, b))
        self.assertEqual(2, k_value)
        self.assertEqual([SUM, 2, AVG, 0.67, MIN, 0, MAX, 1, COUNT, 3], agg_array)

    def test_string_filter(self):
        a, agg_array, b, k_value = get_k_value("x", {("t", "x"): "%abc%"}, False, "t", "char", 0)
        self.assertEqual(("aabc", "babc"), (a, b))
        self.assertEqual(1, k_value)
        self.assertEqual([MIN, "aabc", MAX, "babc"], agg_array)

    def test_number_without_filter(self):
        a, agg_array, b, k_value = get_k_value("x", {}, False, "t", "int", 0)
        self.assertEqual((5, 8), (a, b))
        self.assertEqual(2, k_value)
        self.assertEqual([SUM, 18, AVG, 6, MIN, 5, MAX, 8, COUNT, 3], agg_array)

    def test_date_without_filter(self):
        a, agg_array, b, k_value = get_k_value("x", {}, False, "t", "date", 0)
        self.assertEqual(("'1000-01-01'", "'1000-01-02'"), (a, b))
        self.assertEqual(1, k_value)
        self.assertEqual([MIN, a, MAX, b], agg_array)


class RowCountTest(unittest.TestCase):
    def test_same_table_uses_k_plus_one(self):
        self.assertEqual(4, get_no_of_rows(["a"], 3, ["a"], "t1", "t1", 0, []))

    def test_other_table_with_key_path_uses_two(self):
        self.assertEqual(2, get_no_of_rows(["a"], 3, {"a"}, "t1", "t2", 0, []))

    def test_other_table_without_key_path_uses_one(self):
        self.assertEqual(1, get_no_of_rows(["b"], 3, {"a"}, "t1", "t2", 0, []))


class InsertForInnerTest(unittest.TestCase):
    def test_rows_are_generated_per_table(self):
        agg = _bare_aggregation()
        inserted = []
        agg.insert_attrib_vals_into_table = (
            lambda att_order, attrib_list, rows, tabname: inserted.append(
                (att_order, list(attrib_list), list(rows), tabname)
            )
        )
        temp_vals = []

        max_rows = agg.insert_for_inner(5, "a", 8, 2, [], "t1", temp_vals, 0)

        self.assertEqual(3, max_rows)
        self.assertEqual([[(5, 1), (5, 1), (8, 1)], [(1, 1)]], temp_vals)
        self.assertEqual(2, len(inserted))
        self.assertEqual(("(a,b)", ["a", "b"], [(5, 1), (5, 1), (8, 1)], "t1"), inserted[0])
        self.assertEqual(("(c,d)", ["c", "d"], [(1, 1)], "t2"), inserted[1])

    def test_key_path_limits_other_tables_to_two_rows(self):
        agg = _bare_aggregation()
        inserted = []
        agg.insert_attrib_vals_into_table = (
            lambda att_order, attrib_list, rows, tabname: inserted.append(
                (att_order, list(attrib_list), list(rows), tabname)
            )
        )
        temp_vals = []

        max_rows = agg.insert_for_inner(5, "a", 8, 2, ["c"], "t1", temp_vals, 0)

        self.assertEqual(3, max_rows)
        self.assertEqual([[(5, 1), (5, 1), (8, 1)], [(5, 1), (8, 1)]], temp_vals)
        self.assertEqual(2, len(inserted[1][2]))


class AnalyzeTest(unittest.TestCase):
    def test_analyze_detects_avg(self):
        agg = _bare_aggregation()
        agg.global_aggregated_attributes = [None]

        agg.analyze([SUM, 6, AVG, 3, MIN, 3, MAX, 3, COUNT, 2], "a", [("3",)], 0)

        self.assertEqual(("a", AVG), agg.global_aggregated_attributes[0])

    def test_analyze_rounds_numeric_result(self):
        agg = _bare_aggregation()
        agg.global_aggregated_attributes = [None]

        agg.analyze([SUM, 6.001, AVG, 3.0, MIN, 1, MAX, 4, COUNT, 2], "a", [("2.999",)], 0)

        self.assertEqual(("a", AVG), agg.global_aggregated_attributes[0])

    def test_analyze_keeps_unmatched_attribute(self):
        agg = _bare_aggregation()
        agg.global_aggregated_attributes = [None]

        agg.analyze([SUM, 6, AVG, 3, MIN, 1, MAX, 4, COUNT, 2], "a", [("9",)], 0)

        self.assertIsNone(agg.global_aggregated_attributes[0])


class ExtractJobTest(unittest.TestCase):
    def test_no_groupby_returns_false(self):
        agg = _bare_aggregation()
        agg.global_projected_attributes = ["l_extendedprice"]
        agg.has_groupby = False

        self.assertFalse(agg.doExtractJob("select 1"))
        self.assertEqual([("l_extendedprice", "")], agg.global_aggregated_attributes)


if __name__ == "__main__":
    unittest.main()

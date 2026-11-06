from ...src.pipeline.abstract.Comparator import Comparator


class ResultComparator(Comparator):
    INSERT_BATCH_SIZE = 1000

    def __init__(self, connectionHelper, isHash, core_relations=None):
        super().__init__(connectionHelper, "Result_Comparator", True, core_relations)
        self.isHash = isHash

    def is_match(self, len1, len2):
        self.logger.debug(f"{len1} len1, {len2} len2")
        if self.isHash:
            matched = len1 is not None and len1 == len2
        else:
            matched = super().is_match(len1, len2)
        if matched:
            self._create_working_schema()
        return matched

    def run_diff_queries(self):
        if self.isHash:
            return self.run_hash_diff_queries()
        return super().run_diff_queries()

    def run_hash_diff_queries(self):
        query_r_e = self.connectionHelper.queries.hashtext_query(
            self.r_e, self.get_fully_qualified_table_name(self.r_e)).rstrip().rstrip(';')
        query_r_h = self.connectionHelper.queries.hashtext_query(
            self.r_h, self.get_fully_qualified_table_name(self.r_h)).rstrip().rstrip(';')
        from_clause = " from dual" if self.connectionHelper.config.database == "oracle" else ""
        row = self.connectionHelper.execute_sql_fetchone(f"select ({query_r_e}), ({query_r_h}){from_clause};")
        if row is None:
            return None, None
        return row[0], row[1]

    def insert_data_into_Qh_table(self, res_Qh, table):
        header = str(res_Qh[0]).replace('\'', '').replace(',)', ')')
        qualified_table = self.get_fully_qualified_table_name(table)
        single_cell_result = len(res_Qh) == 2 and len(res_Qh[1]) == 1
        value_rows = []
        for row in res_Qh[1:]:
            temp = []
            nullrow = True
            for val in row:
                if val not in (None, 'None'):
                    nullrow = False
                temp.append('NULL' if val == 'None' else str(val))
            if nullrow:
                continue
            if single_cell_result:
                value = str(temp[0]).replace(',)', ')').replace("'NULL'", "NULL")
                if not value.startswith('('):
                    value = f"('{value}')"
            else:
                value = str(tuple(temp)).replace(',)', ')').replace("'NULL'", "NULL")
            value_rows.append(value)
            if len(value_rows) == self.INSERT_BATCH_SIZE:
                self._insert_rows(qualified_table, header, value_rows)
                value_rows = []
        if value_rows:
            self._insert_rows(qualified_table, header, value_rows)

    def _insert_rows(self, qualified_table, header, value_rows):
        self.connectionHelper.execute_sql(
            [f"INSERT INTO {qualified_table}{header} VALUES {', '.join(value_rows)};"])

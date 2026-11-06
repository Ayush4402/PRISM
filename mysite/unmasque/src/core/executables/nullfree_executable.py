from itertools import islice

from .executable import Executable


def log_result(Res, logger):
    logger.debug("Result size: ", len(Res))
    if len(Res) < 10:
        for row in Res:
            logger.debug(row)


def is_result_nonempty_nullfree(res, logger=None):
    if logger is not None:
        log_result(res, logger)
        #if len(res) < 15:
        #    logger.debug(res[1:])
    if len(res) <= 1:
        return False
    if len(res) == 2 and res[1] is None:
        return False
    for row in islice(res, 1, None):
        if all(val not in (None, 'None') for val in row):
            return True
    return False


def is_result_all_null(res, logger=None):
    if logger is not None:
        # logger.debug("is_result_all_null")
        log_result(res, logger)

    if len(res) <= 1:
        return False
    if len(res) == 2 and res[1] is None:
        return True
    for row in islice(res, 1, None):
        if all(val in (None, 'None') for val in row):
            return True
    return False


def is_result_has_no_data(res, logger=None):
    if logger is not None:
        # logger.debug("is_result_has_no_data")
        log_result(res, logger)

    if len(res) <= 1:
        return True
    return False


def is_result_has_some_data(res, logger=None):
    if logger is not None:
        # logger.debug("is_result_has_some_data")
        log_result(res, logger)

    if len(res) <= 1:
        return False
    if len(res) == 2 and res[1] is None:
        return False
    for row in islice(res, 1, None):
        if any(val not in (None, 'None') for val in row):
            return True
    return False


def is_result_no_full_nullfree_row(res, logger):
    if logger is not None:
        # logger.debug("is_result_no_full_nullfree_row")
        log_result(res, logger)

    if len(res) <= 1:
        return True
    if len(res) == 2 and res[1] is None:
        return True
    for row in islice(res, 1, None):
        if all(val not in (None, 'None') for val in row):
            return False
    return True


class NullFreeExecutable(Executable):
    def __init__(self, connectionHelper):
        super().__init__(connectionHelper, "Null_Free_Executable")

    def is_attrib_all_null(self, Res, attrib):
        idx = Res[0].index(attrib)
        for row in islice(Res, 1, None):
            self.logger.debug(f"{attrib} value: ", row[idx])
            if row[idx] not in (None, 'None'):
                return False
        return True

    def get_attrib_val(self, Res, attrib_idx):
        for row in islice(Res, 1, None):
            if row[attrib_idx] not in (None, 'None'):
                return row[attrib_idx]
        return None

    def is_attrib_equal_val(self, Res, attrib, val):
        idx = Res[0].index(attrib)
        all_null = True
        for row in islice(Res, 1, None):
            self.logger.debug(f"{attrib} value: ", row[idx])
            if row[idx] not in (None, 'None'):
                all_null = False
                if row[idx] != val:
                    return False
        return not all_null

    def get_nullfree_row(self, Res):
        for row in islice(Res, 1, None):
            if 'None' not in row:
                return row
        return None

    def get_all_nullfree_rows(self, Res):
        return [row for row in islice(Res, 1, None) if 'None' not in row]

    def isQ_result_no_full_nullfree_row(self, Res):
        return is_result_no_full_nullfree_row(Res, self.logger)

    def isQ_result_nonEmpty_nullfree(self, Res):
        return is_result_nonempty_nullfree(Res, self.logger)

    def isQ_result_empty(self, Res):
        return is_result_no_full_nullfree_row(Res, self.logger)

    def isQ_result_has_no_data(self, Res):
        return is_result_has_no_data(Res, self.logger)

    def isQ_result_all_null(self, Res):
        return is_result_all_null(Res, self.logger)

    def isQ_result_has_some_data(self, Res):
        return is_result_has_some_data(Res, self.logger)

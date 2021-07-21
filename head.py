from collections import namedtuple

MAX_STRING_LEN = 255
MAX_REL_NAME = 20
MAX_ATTR_NAME = 20
MAX_ATTR_COUNT = 20

RELCAT_FMT = str(MAX_REL_NAME) + 's' + str(MAX_ATTR_COUNT) + 's'
ATTR_FMT = str(MAX_REL_NAME) + 's' + str(MAX_ATTR_NAME) + 'sici??'


# class RC:
#     # return code class, handles errors
#     def __init__(self, code):
#         self.rc = code


class CompOp:
    _dict = {'EQ_OP', 'LT_OP', 'GT_OP', 'LE_OP', 'GE_OP', 'NE_OP', 'NO_OP'}
    # equal, less-than, greater-than, less-than-or-equal, greater-than-or-equal, not-equal, no comparison

    def __init__(self, op: str):
        if str in CompOp._dict:
            self.op = op


class AttrType:
    # the data type this system supports
    _attr_type = {'INT': 'i', 'STR': 's', 'FLOAT': 'f', 'BOOLEAN': '?'}
    _attr_len = {'INT': 4, 'STR': MAX_STRING_LEN, 'FLOAT': 8, 'BOOLEAN': 1}

    def __init__(self, attr_type: str):
        if attr_type in AttrType._attr_type:
            self.type = AttrType._attr_type[attr_type]
            self.len = AttrType._attr_len[attr_type]


class DataAttrInfo:
    # created by passing a list
    # used when create_table is called, to fill in the system ATTR CATALOG table
    def __init__(self, rel_name: str, attr_info: namedtuple):
        self.rel_name = rel_name
        self.attr_name = attr_info.attr_name
        self.offset = attr_info.offset  # offset in order num from beginning of tuple
        self.attr_type = AttrType(attr_info.attr_type).type
        self.attr_len = AttrType(attr_info.attr_type).len
        self.key = attr_info.key
        self.index_exist = False


class RelationInfo:
    # create by passing a list
    # used when create_table is called, to fill in the system RELATION CATALOG table
    def __init__(self, relation_info: list):
        self.rel_name = relation_info[0]  # padding to length of MAX_REL_NAME
        # self.record_len = relation_info[1]
        # self.attr_count = relation_info[2]
        # self.index_count = relation_info[3]
        self.fmt = relation_info[2]  # padding to length of MAX_ATTR_COUNT+1


class Data:
    def __init__(self):
        pass


class RID:
    def __init__(self, page_num, slot_num):
        self._page_num = page_num
        self._slot_num = slot_num

    def get_page_num(self):
        return self._page_num

    def get_slot_num(self):
        return self._slot_num


class Record:
    def __init__(self, data, rid):
        self._data = data
        self._rid = rid

    def get_data(self):
        return self._data

    def get_rid(self):
        return self._rid

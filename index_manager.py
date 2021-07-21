# from head import *
import os
from pickle import dump, load
from BTrees.OOBTree import OOBTree
from record_manager import RecordFileScan, RecordManager, Record, RID
from paged_file_manager import PagedFileManager
import sys
sys.setrecursionlimit(100000)
DISK_SPACE = './root'


class IndexHandle:
    def __init__(self, ix, fp):
        self._ix = ix
        self._fp = fp

    def get_ix(self):
        return self._ix

    def insert_rec(self, rec_l, attr_offset):
        for rec in rec_l:
            key = rec.get_data()[attr_offset]
            if self._ix.has_key(key):
                self._ix[key] = rec.get_rid()
            else:
                self._ix.insert(key, rec.get_rid())
        return True

    def delete_rec(self, rec_l, attr_offset):
        for rec in rec_l:
            key = rec.get_data()[attr_offset]
            if self._ix.has_key(key):
                self._ix.pop(key)
        return True

    def get_rec(self, key):
        if self._ix.has_key(key):
            return self._ix[key]
        else:
            print('error: index key not exist')
            return None

    def force_pages(self):
        self._fp.seek(0, 0)
        dump(self._ix, self._fp)


class IndexManager:

    def __init__(self, root):
        self._root = root
        self._pf_manager = PagedFileManager(root)

    def create_index(self, name, ix_no, attr_typ, attr_offset):
        rec_manager = RecordManager(self._root)
        rec_handle = rec_manager.open_file(name)
        if not rec_handle:
            print('error: index create failed')
            return False
        rec_scan = RecordFileScan(rec_handle, attr_typ, attr_offset, 'NO_OP', None)
        rec = rec_scan.get_next_rec()
        if rec:
            keys = []
            values = []
        while rec:
            keys.append(rec.get_data()[attr_offset])
            values.append(rec.get_rid())
            # rec.check()
            rec = rec_scan.get_next_rec()
        rec_handle.close()
        ix = OOBTree()
        k_v_dict = dict(zip(keys, values))
        ix.update(k_v_dict)

        file_path = os.path.join(self._root, name + 'ix' + str(ix_no) + '.db')
        if os.path.isfile(file_path):
            print('error: file {0} exist'.format(name))
            return None
        else:
            # file_header_size, page_size, page_header_size, schema, record_len, num_records_per_page,
            #                  num_pages_per_group, free_page, free_stack, first_page_num, last_page_num, num_page):
            f = open(file_path, 'wb+')
            dump(ix, f)
            return IndexHandle(ix, f)

    def destroy_index(self, name, ix_no):
        file_path = os.path.join(self._root, name + 'ix' + str(ix_no) + '.db')
        if os.path.isfile(file_path):
            return os.remove(file_path)
        else:
            print('error: file {0} not exist'.format(name))
            return False

    def open_index(self, name, ix_no):
        file_path = os.path.join(self._root, name + 'ix' + str(ix_no) + '.db')
        if os.path.isfile(file_path):
            f = open(file_path, 'rb+')
            try:
                ix = load(f)
                return IndexHandle(ix, f)
            except EOFError:
                ix = None
                return ix
        else:
            print('error: file {0} not exist'.format(name))
            return None

    def close_index(self):
        pass


class IndexScan:
    def __init__(self):
        pass

    def open_scan(self):
        pass

    def get_next_entry(self):
        pass

    def close_scan(self):
        pass


if __name__ == '__main__':
    ix_manager = IndexManager(DISK_SPACE)
    t = ix_manager.create_index('R1', 1, 'i', 0)
    # t = ix_manager.open_index('R1', 1)
    t.get_rec(34).check()
    # t.insert_rec([Record([20, 17], RID(0, 20))], 0)
    # t.force_pages()
    t.get_rec(20).check()
    # print()

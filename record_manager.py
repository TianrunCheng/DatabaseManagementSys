from paged_file_manager import *
import time
DISK_SIZE = './root'


class RID:
    def __init__(self, page_num, slot_num):
        self._page_num = page_num
        self._slot_num = slot_num

    def get_page_num(self):
        return self._page_num

    def get_slot_num(self):
        return self._slot_num

    def check(self):
        print(self._page_num, '-', self._slot_num)


class Record:
    def __init__(self, data, rid):
        self._data = data
        self._rid = rid

    def get_data(self):
        return self._data

    def get_rid(self):
        return self._rid

    def check(self):
        print(self._data, '- (', self.get_rid().get_page_num(), self.get_rid().get_slot_num(), ')')


class RecordFileScan:
    def __init__(self, rec_file_handle, attr_typ,  attr_offset, comp_op, value):
        self._rec_file_handle = rec_file_handle
        self._pf_handle = self._rec_file_handle.get_pf_handle()
        self._cur_record = self.get_first_record()
        self._cur_rid = self._cur_record.get_rid()
        self._attr_typ = attr_typ
        self._attr_offset = attr_offset
        self._comp_op = comp_op
        self._value = value
        # self._cur_rid.check()

    def get_first_record(self):
        first_page = self._pf_handle.get_first_page()
        if not first_page:
            print('empty set')
            return None
        first_page_num = first_page.get_page_num()
        i_page = self._rec_file_handle.get_page(first_page_num)
        # print('first page num', first_page_num)
        rec_l = i_page['rec_l']
        # print(rec_l)
        first_slot_num = 0
        for _ in rec_l:
            if _:
                return Record(_,  RID(first_page_num, first_slot_num))
            first_slot_num += 1
        return None

    def get_next_rec(self):
        if not self._cur_record:
            return None
        while self._cur_record:
            attr = self._cur_record.get_data()[self._attr_offset]
            # print(attr)
            if self._attr_typ == 's':
                attr = attr.decode(encoding='utf-8').strip()
            if self.compare(attr):
                ret_record = self._cur_record
                self._cur_record = self.next_rec()
                return ret_record
            else:
                self._cur_record = self.next_rec()

    def compare(self, op1):
        if self._comp_op == 'EQ_OP':
            return op1 == self._value
        elif self._comp_op == 'LT_OP':
            return op1 < self._value
        elif self._comp_op == 'GT_OP':
            return op1 > self._value
        elif self._comp_op == 'LE_OP':
            return op1 <= self._value
        elif self._comp_op == 'GE_OP':
            return op1 >= self._value
        elif self._comp_op == 'NE_OP':
            return op1 != self._value
        elif self._comp_op == 'NO_OP':
            return True
        print('error: compare type error')
        return False

    def next_rec(self):
        page_num = self._cur_rid.get_page_num()
        slot_num = self._cur_rid.get_slot_num()
        i_page = self._rec_file_handle.get_page(page_num)
        rec_l = i_page['rec_l']
        for i in range(slot_num + 1, len(rec_l)):
            if rec_l[i]:
                self._cur_rid = RID(page_num, i)
                # print('$$$', rec_l)
                return Record(rec_l[i], RID(page_num, i))
        # print('next page -', page_num)
        i_page = self._rec_file_handle.get_next_page(page_num)

        if i_page:
            page_num = i_page['page'].get_page_num()
            rec_l = i_page['rec_l']
            for i in range(0, len(rec_l)):
                if rec_l[i]:
                    self._cur_rid = RID(page_num, i)

                    return Record(rec_l[i], RID(page_num, i))
        return None

    def close_scan(self):
        pass


class RecordFileHandle:
    def __init__(self, pf_handle):
        self._pf_handle = pf_handle
        self._num_rec_per_page = self._pf_handle.get_num_records_per_page()
        self._page_dict = {}

    def get_pf_handle(self):
        return self._pf_handle

    def get_next_page(self, page_num):
        p_header = self._pf_handle.get_page_header(page_num)
        # p_header = cur_page.get_page_header()
        if p_header.has_next:
            return self.get_page(p_header.next_page_num)
        return None

    def get_page(self, page_num):
        # print('%', page_num)
        if page_num not in self._page_dict:
            page = self._pf_handle.get_this_page(page_num)
            if not page:
                return None
            rec_l = page.get_data()
            dif = self._num_rec_per_page - len(rec_l)
            if dif > 0:
                for _ in range(dif):
                    rec_l.append([])
            self._page_dict[page_num] = {'page': page, 'rec_l': rec_l}
        return self._page_dict[page_num]

    def get_rec(self, rid):
        page_num = rid.get_page_num()
        slot_num = rid.get_slot_num()
        rec_l = self.get_page(page_num)['rec_l']
        if slot_num > len(rec_l):
            print('error: record does not exist')
            return None
        if not rec_l[slot_num]:
            print('error: record does not exist')
            return None
        return Record(rec_l[slot_num], rid)

    def insert_rec(self, rec):
        # page(s) in cache
        for p_num, i_page in self._page_dict.items():
            page = i_page['page']
            p_header = page.get_page_header()
            rem = self._num_rec_per_page - p_header.record_num

            if rem > 0:
                slot_num = 0
                for r in i_page['rec_l']:
                    if not r:
                        for t in rec:
                            r.append(t)
                        p_header.record_num += 1
                        page.set_page_header(p_header)
                        # print('$', p_header.record_num)
                        page.mark_dirty()
                        return RID(p_num, slot_num)
                    slot_num += 1
        # pages on disk
        page = self._pf_handle.get_first_page()
        while page:
            p_header = page.get_page_header()
            p_num = p_header.pid
            if not self._page_dict[p_num]:
                rem = self._num_rec_per_page - p_header.record_num
                if rem > 0:

                    rec_l = page.get_data()

                    slot_num = 0
                    for r in rec_l:
                        if not r:
                            for t in rec:
                                r.append(t)
                            p_header.num_page += 1
                            page.set_page_header(p_header)
                            page.mark_dirty()
                            self._page_dict[p_num] = {'page': page, 'rec_l': rec_l}
                            return RID(p_num, slot_num)
                        slot_num += 1

            page = self._pf_handle.get_next_page(p_num)
        # new page
        page = self._pf_handle.alloc_page()
        # print('new')
        p_header = page.get_page_header()
        p_num = p_header.pid
        rec_l = [rec]
        for _ in range(1, self._num_rec_per_page):
            rec_l.append([])
        # print(len(rec_l), rec_l)
        p_header.record_num += 1
        page.set_page_header(p_header)
        page.mark_dirty()
        self._page_dict[p_num] = {'page': page, 'rec_l': rec_l}
        return RID(p_num, 0)

    def delete_rec(self, rid):
        page_num = rid.get_page_num()
        slot_num = rid.get_slot_num()

        if self._page_dict[page_num]:
            page = self._page_dict[page_num]['page']
            rec_l = self._page_dict[page_num]['rec_l']

        else:
            page = self._pf_handle.get_this_page(page_num)
            rec_l = page.get_data()
            self._page_dict[page_num] = {'page': page, 'rec_l': rec_l}

        if slot_num > len(rec_l):
            print('error: record does not exist')
            return False

        if not rec_l[slot_num]:
            print('error: record does not exist')
            return None
        rec_l[slot_num] = []
        page.mark_dirty()
        return True

    def update_rec(self, rec):
        data = rec.get_data()
        rid = rec.get_rid()
        self.delete_rec(rid)
        return self.insert_rec(data)

    def force_pages(self):
        for p_num, i_page in self._page_dict.items():
            page = i_page['page']
            if page.get_dirty_mark():
                if page.get_page_header().record_num == 0:
                    self._pf_handle.dealloc(p_num)
                page.write_data(i_page['rec_l'])
                # print('%%', i_page['rec_l'])

    def close(self):
        self.force_pages()
        self._page_dict = {}
        self._pf_handle.close()


class RecordManager:
    def __init__(self, root):
        self._pf_manager = PagedFileManager(root)

    def create_file(self, name, schema):
        return RecordFileHandle(self._pf_manager.create_file(name, schema))

    def destroy_file(self, name):
        return self._pf_manager.destroy_file(name)

    def open_file(self, name):
        return RecordFileHandle(self._pf_manager.open_file(name))


if __name__ == '__main__':
    rec_manager = RecordManager(DISK_SIZE)
    # rec_handle = rec_manager.create_file('voodo', '?ii')
    # rec_handle.insert_rec([True, 1, 2])
    # print(rec_handle.get_page(0)['rec_l'])

    rec_manager.destroy_file('R')
    rec_handle = rec_manager.create_file('R', 'ii')
    rec_handle = rec_manager.open_file('R')
    rec_handle.insert_rec([1, 1])
    rec_handle.insert_rec([2, 2])
    rec_handle.insert_rec([3, 3])
    rec_handle.insert_rec([4, 3])
    rec_handle.insert_rec([5, 3])
    rec_handle.insert_rec([6, 3])
    rec_handle.insert_rec([7, 3])
    rec_handle.insert_rec([8, 3])
    rec_handle.insert_rec([9, 3])
    rec_handle.insert_rec([10, 3])
    rec_handle.insert_rec([11, 3])
    rec_handle.insert_rec([12, 3])
    rec_handle.insert_rec([13, 3])
    rec_handle.insert_rec([14, 3])
    rec_handle.insert_rec([15, 3])
    rec_handle.insert_rec([16, 3])
    print(rec_handle.get_page(0)['rec_l'])
    # print(rec_handle.get_page(1)['rec_l'])
    rec_scan = RecordFileScan(rec_handle, 'i', 0, 'LT_OP', 7)
    res = rec_scan.get_next_rec()
    while res:
        res.check()
        res = rec_scan.get_next_rec()
    rec_handle.close()
    ''''''''''''''

    s_t = time.time()
    rec_manager = RecordManager(DISK_SIZE)

    # rec_manager.destroy_file('R2')
    rec_handle = rec_manager.create_file('R2', 'i5s')
    for i in range(1, 10):
        rec_handle.insert_rec([i, bytes('abcd' + str(i), encoding='utf-8')])
        print(i)
    print('%.2f sec' % float(time.time() - s_t))

    print(rec_handle.get_page(0)['rec_l'])
    rec_scan = RecordFileScan(rec_handle, 's', 1, 'LT_OP', 'abcd3')
    res = rec_scan.get_next_rec()

    while res:
        print(res.get_data()[1] == b'abcd1')
        res.check()
        res = rec_scan.get_next_rec()
    rec_handle.close()
    # rec_handle.get_rec(RID(1, 0)).check()
    # rec_file_scan = RecordFileScan(rec_handle)
    # rec_file_scan.get_next_rec().check()
    # rec_file_scan.get_next_rec().check()
    # rec_file_scan.get_next_rec().check()
    # rec_file_scan.get_next_rec().check()
    # rec_file_scan.get_next_rec().check()
    # rec_file_scan.get_next_rec().check()
    # rec_file_scan.get_next_rec().check()
    # rec_file_scan.get_next_rec().check()
    # rec_file_scan.get_next_rec().check()
    # rec_file_scan.get_next_rec().check()
    # rec_file_scan.get_next_rec().check()
    # rec_file_scan.get_next_rec().check()
    # rec_file_scan.get_next_rec().check()

"""
[(1, 1), (2, 2), (3, 3), (4, 3), (5, 3), (6, 3), (7, 3), (1, 1)]
[(9, 3), (10, 3), (11, 3), (12, 3), (13, 3), (14, 3), (15, 3), []]

"""


    # print(rid.get_slot_num())
    # rec = rec_handle.get_rec(rid)
    # rec_handle.close()
    # rec_handle = rec_manager.open_file('R')
    # rec_file_scan = RecordFileScan(rec_handle)
    # rec_file_scan.get_next_rec().check()
    # rec_file_scan.get_next_rec().check()
    # rec_file_scan.get_next_rec().check()
    # rec_file_scan.get_next_rec().check()
    # rec_file_scan.get_next_rec().check()
    # rec_file_scan.get_next_rec().check()
    # rec_file_scan.get_next_rec().check()
    # rec_file_scan.get_next_rec().check()
    # rec_file_scan.get_next_rec().check()


    # print(rec_file_scan.get_first_rid().get_page_num())
    # print(rec.get_data(), rec.get_rid().get_page_num(), rec.get_rid().get_slot_num())

import os
from pickle import load, dump
from struct import pack, unpack, calcsize

DISK_SPACE = './root'
SIZE_PAGE = 1024
SIZE_FILE_HEADER = 1024
SIZE_PAGE_HEADER = 64
NUM_PAGES_PER_GROUP = 10


class PageHandle:
    def __init__(self, fp, schema, page_header, page_size, page_header_size):
        self._fp = fp
        self._schema = schema
        self._page_size = page_size
        self._record_len = calcsize(schema)
        self._start_addr = self._fp.tell()
        self._page_header = page_header
        self._page_header_size = page_header_size
        self._dirty_mark = False
        self._pinned_mark = False

        self._rec_addr = self._start_addr + self._page_header_size
        # print(self._fp.tell())

    def get_dirty_mark(self):
        return self._dirty_mark

    def get_page_header(self):
        return self._page_header

    def set_page_header(self, page_header):
        self._page_header = page_header

    def mark_dirty(self):
        self._dirty_mark = True

    def mark_pinned(self):
        self._pinned_mark = True

    def check_addr(self):
        print(self._start_addr)

    def get_data(self):
        rec_l = []
        self._fp.seek(self._rec_addr)
        i = 0
        while i < self._page_header.record_num:
            rec_f = unpack('?', self._fp.read(calcsize('?')))[0]
            if rec_f:
                rec = unpack(self._schema, self._fp.read(self._record_len))
                rec_l.append(rec)
                i += 1
            else:
                self._fp.seek(self._record_len, 1)
                rec_l.append([])
        dif = self._page_header.record_num - len(rec_l)
        for _ in range(dif):
            rec_l.append([])

        return rec_l

    def get_page_num(self):
        # print('page_addr =', self._start_addr)
        # print(self._start_addr, self._file_header_size, self._page_size)
        return self._page_header.pid

    def write_data(self, rec_l):
        n = len(rec_l)
        page_size = n * self._record_len + self._page_header_size
        if page_size > self._page_size:
            print('error: out of page size')
            return False
        else:
            rec_num = 0
            self._fp.seek(self._rec_addr)
            for rec in rec_l:
                if rec:
                    rec_num += 1
                    self._fp.write(pack('?', True))
                    self._fp.write(pack(self._schema,  *rec))
                    # print('&&', rec)
                else:
                    self._fp.write(pack('?', False))
                    self._fp.seek(self._record_len, 1)
        self._page_header.record_num = rec_num
        # print(rec_num)
        self._fp.seek(self._start_addr, 0)
        fmt = 'i?i?l?li'
        page_header = [self._page_header.pid, self._page_header.used_mark, self._page_header.page_header_size,
                       self._page_header.has_next, self._page_header.next_page_num,
                       self._page_header.has_pre, self._page_header.pre_page_num,
                       self._page_header.record_num]
        self._fp.write(pack(fmt, *page_header))
        return True


class PageHeader:
    def __init__(self, pid, used_mark, page_header_size, has_next, next_page_num, has_pre, pre_page_num, record_num):
        self.pid = pid
        self.used_mark = used_mark
        self.page_header_size = page_header_size
        self.has_next = has_next
        self.next_page_num = next_page_num
        self.has_pre = has_pre
        self.pre_page_num = pre_page_num
        self.record_num = record_num


class FileHeader:
    def __init__(self, file_header_size, page_size, page_header_size, schema, record_len, num_records_per_page,
                 num_pages_per_group, free_page, free_stack, first_page_num, last_page_num, num_page):
        self.file_header_size = file_header_size
        self.page_header_size = page_header_size
        self.page_size = page_size
        self.schema = schema
        self.record_len = record_len
        self.num_records_per_page = num_records_per_page
        self.num_pages_per_group = num_pages_per_group
        self.free_page = free_page
        self.free_stack = free_stack
        self.first_page_num = first_page_num
        self.last_page_num = last_page_num
        self.num_page = num_page


class PagedFileHandle:
    def __init__(self, fp):
        self._fp = fp
        # print(self._fp.tell())
        try:
            self._file_header = load(fp)
        except EOFError:
            print('error: page header does not exist')

    def cal_page_addr(self, page_num):
        return self._file_header.file_header_size + page_num * self._file_header.page_size

    def get_num_records_per_page(self):
        return self._file_header.num_records_per_page

    def get_num_page(self):
        return self._file_header.num_page

    def get_first_page(self):
        f_p_num = self._file_header.first_page_num
        # print('$', f_p_num)
        if f_p_num == -1:
            return None
        page_header = self.get_page_header(f_p_num)
        # not used
        if not page_header.used_mark:
            return None
        first_page_addr = self.cal_page_addr(f_p_num)
        self._fp.seek(first_page_addr, 0)
        return PageHandle(self._fp, self._file_header.schema, page_header,
                          self._file_header.page_size, self._file_header.page_header_size)

    def get_last_page(self):
        l_p_num = self._file_header.last_page_num
        if l_p_num == -1:
            return None
        page_header = self.get_page_header(l_p_num)
        # not used
        if not page_header.used_mark:
            return None
        last_page_addr = self.cal_page_addr(l_p_num)
        self._fp.seek(last_page_addr, 0)
        return PageHandle(self._fp, self._file_header.schema, page_header,
                          self._file_header.page_size, self._file_header.page_header_size)

    def get_page_header(self, page_num):
        cur_addr = self._file_header.file_header_size + page_num * self._file_header.page_size

        self._fp.seek(cur_addr, 0)

        try:
            fmt = 'i?i?l?li'
            pid, used_mark, page_header_size, has_next, next_page_num, has_pre, pre_page_num, record_num = unpack(fmt, self._fp.read(calcsize(fmt)))
            page_header = PageHeader(pid, used_mark, page_header_size, has_next, next_page_num, has_pre, pre_page_num, record_num)
            return page_header
        except Exception:
            print('error: load page failed')
            return None

    def update_page_header(self, page_num, page_header):
        cur_addr = self._file_header.file_header_size + page_num * self._file_header.page_size

        self._fp.seek(cur_addr, 0)
        fmt = 'i?i?l?li'
        # print(page_header)
        try:
            p = pack(fmt, *page_header)
            self._fp.write(p)
            return True
        except EOFError:
            print('error: update page header fail')
            return False

    def get_next_page(self, cur_page_num):
        page_header = self.get_page_header(cur_page_num)
        # print(page_header.pid, page_header.nxt_page_num)
        if not page_header:
            return None
        if not page_header.used_mark:
            print('error: page not exist')
            return False
        if page_header.has_next:
            # print('next -', page_header.next_page_num)
            nxt_num = page_header.next_page_num
            nxt_addr = self.cal_page_addr(nxt_num)
            nxt_header = self.get_page_header(nxt_num)
            self._fp.seek(nxt_addr, 0)
            return PageHandle(self._fp, self._file_header.schema, nxt_header,
                              self._file_header.page_size, self._file_header.page_header_size)
        else:
            print('error: this is the last page')
            return None

    def get_pre_page(self, cur_page_num):
        page_header = self.get_page_header(cur_page_num)
        if not page_header:
            return None
        if not page_header.used_mark:
            print('error: page not exist')
            return False
        if page_header.has_pre:
            pre_num = page_header.pre_page_num
            pre_addr = self.cal_page_addr(pre_num)
            pre_header = self.get_page_header(pre_num)
            self._fp.seek(pre_addr, 0)
            return PageHandle(self._fp, self._file_header.schema, pre_header,
                              self._file_header.page_size, self._file_header.page_header_size)
        else:
            print('error: this is the first page')
            return None

    def get_this_page(self, cur_page_num):
        page_header = self.get_page_header(cur_page_num)
        if not page_header:
            print('error: page not exist')
            return None
        if not page_header.used_mark:
            print('error: page not exist')
            return None
        cur_addr = self.cal_page_addr(cur_page_num)
        self._fp.seek(cur_addr, 0)
        return PageHandle(self._fp, self._file_header.schema, page_header,
                          self._file_header.page_size, self._file_header.page_header_size)

    def alloc_page(self):
        n = len(self._file_header.free_stack)

        if self._file_header.free_page == -1:
            self._fp.seek(0, 2)
            ret_addr = self._file_header.file_header_size + self._file_header.num_page * self._file_header.page_size
            self._file_header.num_page += 1
        else:
            if n == 1:
                ret_addr = self._file_header.free_page
                self._file_header.free_page = self._file_header.free_stack[0]
                if self._file_header.free_page != -1:
                    self._fp.seek(self._file_header.free_page)
                    fmt = '%uL' % self._file_header.num_pages_per_group
                    self._file_header.free_stack = unpack(fmt, self._fp.read(calcsize(fmt)))
                self._fp.seek(0, 0)
            else:
                ret_addr = self._file_header.free_stack.pop()
        page_num = int((ret_addr - self._file_header.file_header_size) / self._file_header.page_size)
        # last page
        l_p = self.get_last_page()
        if l_p:
            l_p_num = l_p.get_page_num()
            # print('*', l_p_num)
            l_p_header = self.get_page_header(l_p_num)
            l_header = [l_p_num, l_p_header.used_mark, self._file_header.page_header_size, True, page_num,
                        l_p_header.has_pre, l_p_header.pre_page_num, l_p_header.record_num]
            # print('update -', l_p_num, page_num)
            self.update_page_header(l_p_num, l_header)
            has_pre = True
        else:
            l_p_num = -1
            has_pre = False
            self._file_header.first_page_num = page_num

        page_header = [page_num, True, self._file_header.page_header_size, False, -1, has_pre, l_p_num, 0]
        self._file_header.last_page_num = page_num
        # print('*', page_num)
        self._fp.seek(ret_addr)
        fmt = 'i?i?l?li'
        # print(page_header)
        p = pack(fmt, *page_header)
        self._fp.write(p)
        self._file_header.last_page_addr = ret_addr
        self._fp.seek(0, 0)
        dump(self._file_header, self._fp)
        self._fp.seek(ret_addr)
        return PageHandle(self._fp, self._file_header.schema, PageHeader(*page_header),
                          self._file_header.page_size, self._file_header.page_header_size)

    def dealloc_page(self, page_num):
        page_addr = self._file_header.file_header_size + page_num * self._file_header.page_size
        page_header = self.get_page_header(page_num)
        if not page_header:
            return False
        if not page_header.used_mark:
            print('error: page not exist')
            return False
        if page_header.has_pre:
            pre_p = self.get_pre_page(page_num)
            pre_p_num = pre_p.get_page_num()
            # pre_p_addr = self._file_header.file_header_size + pre_p_num * self._file_header.page_size
            pre_p_header = self.get_page_header(pre_p_num)

            if page_header.has_next:
                nxt_p = self.get_next_page(page_num)
                nxt_p_num = nxt_p.get_page_num()
                # nxt_p_addr = self._file_header.file_header_size + nxt_p_num * self._file_header.page_size
                nxt_p_header = self.get_page_header(nxt_p_num)
                pre_header = [pre_p_num, pre_p_header.used_mark, self._file_header.page_header_size, True,
                              nxt_p_num, pre_p_header.has_pre, pre_p_header.pre_page_num, pre_p_header.record_num]
                nxt_header = [nxt_p_num, nxt_p_header.used_mark, self._file_header.page_header_size,
                              nxt_p_header.has_next, nxt_p_header.next_page_num,
                              True, pre_p_num, nxt_p_header.record_num]
                self.update_page_header(pre_p_num, pre_header)
                self.update_page_header(nxt_p_num, nxt_header)

            else:
                pre_header = [pre_p_num, pre_p_header.used_mark, self._file_header.page_header_size, False, -1,
                              pre_p_header.has_pre, pre_p_header.pre_page_num, pre_p_header.record_num]
                self.update_page_header(pre_p_num, pre_header)
                self._file_header.last_page_num = pre_p_num
        else:
            if page_header.has_next:
                nxt_p = self.get_next_page(page_num)
                nxt_p_num = nxt_p.get_page_num()
                nxt_p_header = self.get_page_header(nxt_p_num)
                nxt_header = [nxt_p_num, nxt_p_header.used_mark, self._file_header.page_header_size, nxt_p_header.has_next,
                              nxt_p_header.next_page_addr, False, -1, nxt_p_header.record_num]
                self.update_page_header(nxt_p_num, nxt_header)
                self._file_header.first_page_num = nxt_p_num
            else:
                self._file_header.last_page_num = -1
                self._file_header.first_page_num = -1

        n = len(self._file_header.free_stack)
        if self._file_header.free_page == -1:
            self._file_header.free_page = page_addr
            self._fp.seek(0, 0)
            dump(self._file_header, self._fp)
            return True
        if n == self._file_header.num_pages_per_group:
            self._file_header.free_page = page_addr
            save_addr = self._file_header.free_stack[0]
            self._fp.seek(save_addr)
            fmt = '%uL' % self._file_header.num_pages_per_group
            self._fp.write(pack(fmt, *self._file_header.free_stack))
            self._file_header.free_stack = [save_addr]
            # update file header
            self._fp.seek(0, 0)
            dump(self._file_header, self._fp)
            return True
        else:
            self._file_header.free_stack.append(page_addr)
            self._fp.seek(0, 0)
            dump(self._file_header, self._fp)
            return True

    def close(self):
        self._fp.close()


class PagedFileManager:
    def __init__(self, root):
        self._root = root

    def create_file(self, name, schema):
        file_path = os.path.join(self._root, name + '.db')
        if os.path.isfile(file_path):
            print('error: file {0} exist'.format(name))
            return None
        else:
            # file_header_size, page_size, page_header_size, schema, record_len, num_records_per_page,
            #                  num_pages_per_group, free_page, free_stack, first_page_num, last_page_num, num_page):
            f = open(file_path, 'wb+')
            record_len = calcsize(schema)
            num_records_per_page = int((SIZE_PAGE - SIZE_PAGE_HEADER) / record_len)
            f_header = FileHeader(SIZE_FILE_HEADER, SIZE_PAGE, SIZE_PAGE_HEADER, schema, record_len,
                                  num_records_per_page, NUM_PAGES_PER_GROUP, -1, [-1], -1, -1, 0)
            dump(f_header, f)
            f.seek(0, 0)
            return PagedFileHandle(f)

    def destroy_file(self, name):
        file_path = os.path.join(self._root, name + '.db')
        if os.path.isfile(file_path):
            return os.remove(file_path)
        else:
            print('error: file {0} not exist'.format(name))
            return False

    def open_file(self, name):
        file_path = os.path.join(self._root, name + '.db')
        if os.path.isfile(file_path):
            f = open(file_path, 'rb+')
            return PagedFileHandle(f)
        else:
            print('error: file {0} not exist'.format(name))
            return None

    @ staticmethod
    def close_file(pf_handle):
        return pf_handle.close()


if __name__ == '__main__':
    pf_manager = PagedFileManager(DISK_SPACE)
    pf_manager.destroy_file('R')
    # page_manager = pf_manager.open_file('R')
    page_manager = pf_manager.create_file('R', 'ii')

    if page_manager:
        a = page_manager.alloc_page()
        b = page_manager.alloc_page()
        c = page_manager.alloc_page()
        rec_list = [(1, 1), [],  (2, 2)]
        a.write_data(rec_list)
        print(a.get_data())
    #     print('page ID a -', a.get_page_num())
    #     print('page ID b -', b.get_page_num())
    #     # b.check_addr()
    #     print('page ID c -', c.get_page_num())
    #     page_manager.dealloc_page(2)
    #
    #     d = page_manager.alloc_page()
    #     print('page ID d -', d.get_page_num())
    #     f = page_manager.get_next_page(1)
    #     # d = page_manager.get_first_page()
    #     if d:
    #         print('page ID d -', f.get_page_num())


        # d.check_addr()
        # e = page_manager.alloc_page()
        # f = page_manager.alloc_page()
        # g = page_manager.alloc_page()
        # print('page ID e -', e.get_page_num())
        # print('page ID f -', f.get_page_num())
        # print('page ID g -', g.get_page_num())
        # page_manager.dealloc_page(4)
        # page_manager.dealloc_page(5)
        # h = page_manager.alloc_page()
        # i = page_manager.alloc_page()
        # print('page ID h -', h.get_page_num())
        # print('page ID i -', i.get_page_num())
        # j = page_manager.get_pre_page(2)
        # print('pre_page ID', j.get_page_num())
        # k = page_manager.get_next_page(2)
        # print('nxt_page ID', j.get_page_num())

    # page_header = [32, False, -1, False, -1]
    # fmt = 'i?L?L'
    # for i in page_header:
    #     print(i)
    # p = pack(fmt, *page_header)


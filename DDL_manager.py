from head import *
import shutil
from record_manager import RecordManager, RecordFileScan
from index_manager import IndexManager
import os
from struct import pack, unpack, calcsize
from collections import namedtuple


class SystemManager:
    def __init__(self):
        self.managers = []  # managers[0]=PagedFileManager, managers[0]=RMManager
        self.handles = []

    def create_db(self, db_name: str):
        if os.path.isdir(db_name):
            print('database already exist, cannot be created again')
        else:
            os.mkdir(db_name)
            self.managers.append(RecordManager('./' + db_name))
            self.managers[0].create_file('relcat', RELCAT_FMT)
            self.managers[0].create_file('attrcat', ATTR_FMT)
            self.managers = []  # shift out of database dir after creation

    @staticmethod
    def destroy_db(db_name: str):
        if os.path.isdir(db_name):
            shutil.rmtree(db_name)
        else:
            print('database already destroyed or does not exist')

    def open_db(self, db_name: str):
        # called when USE DATABASE is queried, let sys_manager move to the database dir
        if os.path.isdir(db_name):
            self.managers.append(RecordManager('./' + db_name))
            self.managers.append(IndexManager('./' + db_name))
            self.handles.append(self.managers[0].open_file('relcat'))
            self.handles.append(self.managers[0].open_file('attrcat'))
        else:
            print('trying to open an non-exist database' + '\n')

    def close_db(self):
        if len(self.managers) > 0:
            # self.managers[0].close_file()
            self.managers = []
            self.handles = []
        else:
            print('database already closed')

    def create_table(self, rel_name: str, attr_lis: list):
        # write tuple for relation schema to relcat
        # write tuple for each attribute in this relation to attrcat
        # create file for this table
        rel_info = []
        rel_info.append(rel_name)
        fmt = ''
        attr_lis_byte = []
        for _ in attr_lis:
            cur_attr = DataAttrInfo(rel_name, _)
            if cur_attr.attr_type == 's':
                fmt = fmt + str(MAX_STRING_LEN) + cur_attr.attr_type
            else:
                fmt = fmt + cur_attr.attr_type
            cur_attr_byte = [bytes(rel_name, 'utf-8').ljust(MAX_REL_NAME),
                                    bytes(cur_attr.attr_name, 'utf-8').ljust(MAX_ATTR_NAME),
                                    cur_attr.offset, bytes(cur_attr.attr_type, 'utf-8'), cur_attr.attr_len,
                                    cur_attr.key, cur_attr.index_exist]
            attr_lis_byte.append(cur_attr_byte)
        rel_info.append(fmt)
        rel_info_byte = [bytes(rel_info[0], 'utf-8').ljust(MAX_REL_NAME),
                                           bytes(rel_info[1], 'utf-8').ljust(MAX_ATTR_COUNT)]
        if len(self.managers) == 0:
            print('no database opened'+'\n')
        else:
            self.managers[0].create_file(rel_info[0], rel_info[1])
            self.handles[0].insert_rec(rel_info_byte)
            for _ in attr_lis_byte:
                self.handles[1].insert_rec(_)
            self.handles[0].force_pages()
            self.handles[1].force_pages()

    def create_index(self, rel_name: str, attr_name: str):
        attrcat_scan = RecordFileScan(self.handles[1], 's', 0, 'EQ_OP', rel_name)

        res = attrcat_scan.get_next_rec()
        while res:
            if res.get_data()[1] == bytes(attr_name, 'utf-8').ljust(MAX_ATTR_NAME):
                break
            res = attrcat_scan.get_next_rec()

        if res.get_data()[6]:
            print('Index already exist')
        else:
            data = []
            for i in range(6):
                data.append(res.get_data()[i])
            data.append(True)
            rid = res.get_rid()
            self.handles[1].update_rec(Record(data, rid))
            self.handles[1].force_pages()  # alter ATTR_CATALOG
            new_ix = self.managers[1].create_index(
                rel_name, res.get_data()[2], res.get_data()[3], res.get_data()[2]
            )
            new_ix.force_pages()

    def drop_table(self, rel_name: str):
        self.managers[0].destroy_file(rel_name)
        attrcat_scan = RecordFileScan(self.handles[1], 's', 0, 'EQ_OP', rel_name)
        relcat_scan = RecordFileScan(self.handles[0], 's', 0, 'EQ_OP', rel_name)

        cur_rel = relcat_scan.get_next_rec()
        while cur_rel:
            self.handles[0].delete_rec(cur_rel.get_rid())
            cur_rel = attrcat_scan.get_next_rec()

        cur_attr = attrcat_scan.get_next_rec()
        while cur_attr:
            if cur_attr.get_data()[6]:
                self.managers[1].destroy_index(rel_name, cur_attr.get_data()[2])
            self.handles[1].delete_rec(cur_attr.get_rid())
            cur_attr = attrcat_scan.get_next_rec()

        self.handles[0].force_pages()
        self.handles[1].force_pages()

    def drop_index(self, rel_name: str, attr_name: str):
        attrcat_scan = RecordFileScan(self.handles[1], 's', 0, 'EQ_OP', rel_name)
        cur_attr = attrcat_scan.get_next_rec()
        while cur_attr:
            if cur_attr.get_data()[1] == bytes(attr_name, 'utf-8').ljust(MAX_ATTR_NAME):
                if cur_attr.get_data()[6]:
                    self.managers[1].destroy_index(rel_name, cur_attr.get_data()[2])
                    data = []
                    for i in range(6):
                        data.append(cur_attr.get_data()[i])
                    data.append(True)
                    rid = cur_attr.get_rid()
                    self.handles[1].update_rec(Record(data, rid))
                    self.handles[1].force_pages()
                else:
                    print('Dropping none existent index')
                break
            cur_attr = attrcat_scan.get_next_rec()


if __name__ == '__main__':
    sm = SystemManager()
    sm.create_db('Abracadabra')
    sm.open_db('Abracadabra')
    ATTR = namedtuple('attr', ['attr_name', 'attr_type', 'offset', 'key'])
    p0 = ATTR(*['x', 'INT', 0, True])
    p1 = ATTR(*['y', 'INT', 1, False])
    sm.create_table('voodoo', [p0, p1])
    # self.handles[0] = sm.managers[0].open_file('relcat')
    # self.handles[1] = sm.managers[0].open_file('attrcat')
    # print('!', self.handles[0].get_rec(RID(0, 0)).get_data())



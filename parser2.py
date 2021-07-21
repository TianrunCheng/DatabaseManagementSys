from enum import Enum, auto
from tokenizer import Keywords as K, Punctuations as P, Tokenizer, TokenType

ID = TokenType.IDENTIFIER
CON = TokenType.CONSTANT


class Symbol:
    def __init__(self, name, ref=[]):
        self._name = name
        # self._type = typ
        # self._cat = cat
        self._ref = ref

    def equal(self, name):
        if self._name == name:
            return True
        else:
            return False

    def set_ref(self, ref):
        if len(self._ref) == 0:
            self._ref.append(ref)
        else:
            print('update symb ref failed -- existed ref')

    def get_ref(self):
        return self._ref

    def get_name(self):
        return self._name


class Quat:
    def __init__(self, action, op1, op2):
        self._action = action
        self._op1 = op1
        self._op2 = op2

    def get_qt(self):
        return '({0}, {1}, {2})'.format(self._action, self.get_op1(), self.get_op2())

    def get_action(self):
        return self._action

    def get_op1(self):
        if isinstance(self._op1, Quat):
            return self._op1.get_qt()
        elif isinstance(self._op1, Symbol):
            return self._op1.get_name()
        elif isinstance(self._op1, list):
            res = []
            for _ in self._op1:
                if isinstance(_, Quat):
                    res.append(_.get_qt())
                else:
                    res.append(_.get_name())
            return res
        else:
            return str(self._op1)

    def get_op2(self):
        if isinstance(self._op2, Quat):
            return self._op2.get_qt()
        elif isinstance(self._op2, Symbol):
            return self._op2.get_name()
        elif isinstance(self._op2, list):
            res = []
            for _ in self._op2:
                res.append(_.get_name())
            return res
        else:
            return str(self._op2)


class ActivityRecord:
    cur_level = -1

    def __init__(self, pre_record):
        ActivityRecord.cur_level += 1
        self._level = ActivityRecord.cur_level
        self._col_l = []
        self._pre_record = pre_record
        self._tab_l = []

    def get_pre_record(self):
        return self._pre_record

    def get_tab_l(self):
        return self._tab_l

    def check_symb(self):
        # table
        for tab in self._tab_l:
            if not tab.get_ref():
                record = self.get_pre_record()
                while record:
                    for t in record.get_tab_l:
                        if t.equal(tab.get_name):
                            tab.set_ref(t.get_ref()[0])
                            break
                    if tab.get_ref():
                        break
                    record = record.get_pre_record()
                if not tab.get_ref():
                    print('error: unknown table {0}'.format(tab.get_name()))
                    return False
        # column
        for col in self._col_l:
            if not col.get_ref():
                tab_col_l = col.get_name().split('.')
                # only col name
                if len(tab_col_l) == 1:
                    record = self
                    while record:
                        tab_l = record.get_tab_l()
                        ref = []
                        for tab in tab_l:
                            if tab.get_ref():
                                for c in tab.get_ref()[0].get_col_l():
                                    if col.equal(c.get_name()):
                                        ref.append(c)
                        n = len(set(ref))
                        if n == 1:
                            col.set_ref(ref[0])
                            break
                        if n > 1:
                            print('error: column {0} is ambiguous'.format(col.get_name()))
                            return False
                        else:
                            record = record.get_pre_record()
                # tabName.colName
                if len(tab_col_l) == 2:
                    tab_name = tab_col_l[0]
                    col_name = tab_col_l[1]
                    record = self
                    while record:
                        tab_l = record.get_tab_l()
                        for tab in tab_l:
                            if tab.equal(tab_name):
                                if tab.get_ref():
                                    for c in tab.get_ref()[0].get_col_l():
                                        if c.get_name() == col_name:
                                            col.set_ref(c)
                                            break
                            if col.get_ref():
                                break
                        if col.get_ref():
                            break
                        record = record.get_pre_record()
                if not col.get_ref():
                    print('error: unknown column {0}'.format(col.get_name()))
                    return False
        return True

    def add_tab(self, name, ref):
        tab = Symbol(name, ref)
        self._tab_l.append(tab)
        return tab

    def add_col(self, name, ref):
        col = Symbol(name, ref)
        self._col_l.append(col)
        return col

    def find_col(self, name):
        for col in self._col_l:
            if col.equal(name):
                return col
        return None

    def find_tab(self, name):
        for tab in self._tab_l:
            if tab.equal(name):
                return tab
        return None

    def last_tab_ref(self):
        if self._tab_l[-1]:
            return self._tab_l[-1].get_ref()
        else:
            return None

    def last_col_ref(self):
        if self._col_l[-1]:
            return self._col_l[-1].get_ref()
        else:
            return None

    def update_col(self, i, ref):
        try:
            self._col_l[i].set_ref(ref)
        except IndexError:
            print('update symb failed -- index error')


class Parser:

    def __init__(self, inputs):
        self._token_l = Tokenizer().run(inputs)
        self._cur_pos = 0
        self._cur_act_record = None
        self._act_record_l = []
        self._sem_stack = []
        self._quat_stack = []
        self._tab_l = []

    def set_schema(self, tab_l):
        self._tab_l = tab_l

    def check_quat_action(self):
        for qt in self._quat_stack:
            print('-', qt.get_qt())
        print(len(self._sem_stack))

    def read(self):
        if self._cur_pos < len(self._token_l):
            return self._token_l[self._cur_pos]
        else:
            return None

    def next(self):
        self._cur_pos += 1

    def match(self, *args, optional=False):
        pos = self._cur_pos
        f = True
        for arg in args:
            if hasattr(arg, '__call__'):
                if not arg():
                    f = False
                    self._cur_pos = pos
                    break
            else:
                if not self.read():
                    f = False
                    self._cur_pos = pos
                    break
                # self.read().tostring()
                if self.read().match(arg):
                    self.next()
                else:
                    f = False
                    self._cur_pos = pos
                    break
        return f or optional

    # def optional(self, *args, many=None):
    #     if not self.read():
    #         return True
    #     if self.match(*args):
    #         if many:
    #             self.many(*many)
    #         return True
    #     else:
    #         return True

    def many(self, *args):
        if not self.read():
            return True
        while self.match(*args):
            if not self.read():
                return True
            continue
        return True

    def tree(self, *args, optional=False):
        f = False
        for arg in args:
            if self.match(*arg):
                f = True
                break
        return f or optional

    def stmt_block(self):
        return self.match(self.stmt)

    def stmt(self):
        return self.tree([self.preparable_stmt], [self.comment_stmt])

    def preparable_stmt(self):
        return self.tree([self.alter_stmt], [self.create_stmt], [self.delete_stmt], [self.drop_stmt],
                         [self.explain_stmt], [self.insert_stmt], [self.select_stmt], [self.show_stmt],
                         [self.update_stmt], [self.upsert_stmt])

    def alter_stmt(self):
        # [self.alter_user_stmt] not considered
        return self.tree([self.alter_ddl_stmt])

    def alter_ddl_stmt(self):
        return self.tree([self.alter_table_stmt], [self.alter_index_stmt], [self.alter_view_stmt],
                         [self.alter_database_stmt])

    def alter_table_stmt(self):
        return self.tree([self.alter_onetable_stmt], [self.alter_rename_table_stmt])

    def alter_onetable_stmt(self):
        f = self.match(K.ALTER, K.TABLE)
        if f:
            self.match(K.IF, K.EXISTS)
            f = self.match(self.relation_expr, self.alter_table_cmds)
        return f

    def relation_expr(self):
        f = self.match(self.table_name)
        if f:
            self.match(P('*'))
        if not f:
            f = self.match(K.ONLY)
            if f:
                f = self.match(self.table_name)
                if not f:
                    f = self.match(P('('), self.table_name, P(')'))
        return f

    def table_name(self):
        f = self.match(ID)
        return f

    def alter_table_cmds(self):
        f = self.match(self.alter_table_cmd)
        while f and self.match(P(',')):
            f = self.match(self.alter_table_cmd)
        return f

    def alter_table_cmd(self):
        # RENAME
        f = self.match(K.RENAME, self.opt_column, self.column_name, K.TO, self.column_name)
        if not f:
            f = self.match(K.RENAME, K.CONSTRAINT, self.column_name, K.TO, self.column_name)
        # ADD
        if not f:
            f = self.match(K.ADD)
            if f:
                f = self.match(self.table_constraint, self.opt_validate_behavior)
                if not f:
                    self.match(K.COLUMN)
                    self.match(K.IF, K.NOT, K.EXISTS)
                    f = self.match(self.column_def)
                return f
        # ALTER
        if not f:
            f = self.match(K.ALTER, self.opt_column, self.column_name)
            if f:
                f = self.match(self.alter_column_default)
                if not f:
                    f = self.match(K.DROP, K.NOT, K.NULL)
                if not f:
                    f = self.match(K.SET, K.NOT, K.NULL)
                if not f:
                    f = self.match(self.opt_set_data, K.TYPE, self.typename, self.opt_alter_column_using)
                return f
        # DROP
        if not f:
            f = self.match(K.DROP)
            if f:
                f = self.match(self.opt_column)
                if f:
                    self.match(K.IF, K.EXISTS)
                    f = self.match(self.column_name)
                else:
                    f = self.match(K.CONSTRAINT)
                    if f:
                        self.match(K.IF, K.EXISTS)
                        f = self.match(self.constraint_name)
                if f:
                    f = self.match(self.opt_drop_behavior)
                return f
        # VALIDATE
        if not f:
            f = self.match(K.VALIDATE, K.CONSTRAINT, self.constraint_name)
        # PARTITION
        if not f:
            f = self.match(self.partition_by)
        return f

    def table_constraint(self):
        self.match(K.CONSTRAINT, self.constraint_name)
        f = self.match(self.constraint_elem)
        return f

    def constraint_elem(self):
        f = self.match(K.CHECK, P('('), self.a_expr, P(')'))
        if not f:
            f = self.match(K.PRIMARY, K.KEY, P('('), self.index_params, P(')'))
        if not f:
            f = self.match(K.UNIQUE, P('('), self.index_params, P(')'), self.opt_storing,
                           self.opt_interleave, self.opt_partition_by)
        if not f:
            f = self.match(K.FOREIGN, K.KEY, P('('), self.name_list, P(')'), K.REFERENCES, self.table_name,
                           self.opt_column_list, self.key_match, self.reference_actions)
        return f

    def index_params(self):
        f = self.match(self.index_elem)
        while f and self.match(P(',')):
            f = self.match(self.index_elem)
        return f

    def index_elem(self):
        f = self.match(self.a_expr, self.opt_asc_desc, self.opt_nulls_order)
        return f

    def opt_storing(self):
        self.match(self.storing, P('('), self.name_list, P(')'))
        return True

    def storing(self):
        f = self.match(K.COVERING)
        if f:
            self.match(K.STORING)
        return f

    def opt_interleave(self):
        self.match(K.INTERLEAVE, K.IN, K.PARENT, self.table_name, P('('), self.name_list, P(')'))
        return True

    def opt_partition_by(self):
        self.match(self.partition_by)
        return True

    def opt_column_list(self):
        self.match(P('('), self.name_list, P(')'))
        return True

    def key_match(self):
        f = self.match(K.MATCH)
        if f:
            f = self.match(K.SIMPLE)
            if not f:
                f = self.match(K.FULL)
            if not f:
                print('error missing MATCH param')
                return False
        return True

    def reference_actions(self):
        f = self.match(self.reference_on_update)
        if f:
            self.match(self.reference_on_delete)
        else:
            f = self.match(self.reference_on_delete)
            if f:
                self.match(self.reference_on_update)
        return True

    def reference_on_update(self):
        f = self.match(K.ON, K.UPDATE, self.reference_action)
        return f

    def reference_on_delete(self):
        f = self.match(K.ON, K.DELETE, self.reference_action)
        return f

    def reference_action(self):
        f = self.match(K.RESTRICT)
        if not f:
            f = self.match(K.CASCADE)
        if not f:
            f = self.match(K.SET)
            if f:
                f = self.match(K.NULL)
                if not f:
                    f = self.match(K.DEFAULT)
        return f

    def opt_validate_behavior(self):
        self.match(K.NOT, K.VALID)
        return True

    def alter_column_default(self):
        f = self.match(K.SET, K.DEFAULT, self.a_expr)
        if not f:
            f = self.match(K.DROP, K.DEFAULT)
        return f

    def opt_set_data(self):
        self.match(K.SET, K.DATA)
        return True

    def constraint_name(self):
        f = self.match(ID)
        return f

    def typename(self):
        f = self.match(self.simple_typename)
        if f:
            f = self.match(self.opt_array_bounds)
            if not f:
                f = self.match(K.ARRAY)
        return f

    def simple_typename(self):
        f = self.match(self.character_with_length)
        if not f:
            f = self.match(self.const_typename)
        return f

    def const_typename(self):
        f = self.match(K.INT)
        if not f:
            f = self.match(K.FLOAT, self.opt_float)
        if not f:
            f = self.match(K.BOOLEAN)
        if not f:
            f = self.match(K.BOOL)
        if not f:
            f = self.match(self.character_without_length)
        if not f:
            f = self.match(K.DATE)
        return f

    def opt_float(self):
        self.match(P('('), CON, P(')'))
        return True

    def character_without_length(self):
        f = self.match(self.character_base)
        return f

    def character_base(self):
        f = self.match(K.CHAR)
        if not f:
            f = self.match(K.VARCHAR)
        if not f:
            f = self.match(K.STRING)
        return f

    def character_with_length(self):
        f = self.match(self.character_base, P('('), CON, P(')'))
        return f

    def opt_array_bounds(self):
        self.match(P('['), P(']'))
        return True

    def opt_alter_column_using(self):
        self.match(K.USING, self.a_expr)
        return True

    def opt_drop_behavior(self):
        f = self.match(K.CASCADE)
        if not f:
            self.match(K.RESTRICT)
        return True

    def partition_by(self):
        f = self.match(K.PARTITION, K.BY)
        if f:
            f = self.match(K.LIST, P('('), self.name_list, P(')'), P('('), self.list_partitions, P(')'))
            if not f:
                f = self.match(K.RANGE, P('('), self.name_list, P(')'), P('('), self.range_partitions, P(')'))
            if not f:
                f = self.match(K.NOTHING)
        return f

    def list_partitions(self):
        f = self.match(self.list_partition)
        while f and self.match(P(',')):
            f = self.match(self.list_partition)

    def list_partition(self):
        f = self.match(self.partition, K.VALUES, K.IN, P('('), self.expr_list, P(')'), self.opt_partition_by)
        return f

    def partition(self):
        f = self.match(K.PARTITION, self.partition_name)
        return f

    def partition_name(self):
        return self.match(self.unrestricted_name)

    def range_partitions(self):
        f = self.match(self.range_partition)
        while f and self.match(P(',')):
            f = self.match(self.range_partition)
        return f

    def range_partition(self):
        f = self.match(self.partition, K.VALUES, K.FROM, P('('), self.expr_list, P(')'),
                       K.TO, P('('), self.expr_list, P(')'), self.opt_partition_by)
        return f

    def opt_column(self):
        self.match(K.COLUMN)
        return True

    def column_name(self):
        f = self.match(ID)
        return f

    def column_def(self):
        f = self.match(self.column_name, self.typename, self.col_qual_list)
        return f

    def col_qual_list(self):
        while self.match(self.col_qualification):
            continue
        return True

    def col_qualification(self):
        self.match(K.CONSTRAINT, self.constraint_name)
        f = self.match(self.col_qualification_elem)
        return f

    def col_qualification_elem(self):
        f = self.match(K.UNIQUE)
        if not f:
            f = self.match(K.PRIMARY, K.KEY)
        if not f:
            f = self.match(K.CHECK, P('('), self.a_expr, P(')'))
        if not f:
            f = self.match(K.DEFAULT, self.b_expr)
        if not f:
            f = self.match(K.REFERENCES, self.table_name, self.opt_name_parens, self.key_match, self.reference_actions)
        if not f:
            f = self.match(K.AS, P('('), self.a_expr, P(')'), K.SORTED)
        if not f:
            f = self.match(K.NOT)
            if f:
                f = self.match(K.NULL)
            else:
                f = self.match(K.NULL)
        return f

    def opt_name_parens(self):
        self.match(P('('), ID, P(')'))
        return True

    def alter_index_stmt(self):
        pass

    def alter_view_stmt(self):
        pass

    def alter_database_stmt(self):
        pass

    def create_stmt(self):
        return self.tree([self.create_ddl_stmt])

    def create_ddl_stmt(self):
        # [self.create_index_stmt], [self.create_view], [self.table_as_stmt]
        return self.tree([self.create_database_stmt], [self.create_table_stmt])

    def create_database_stmt(self):
        f = self.match(K.CREATE, K.DATABASE)
        if f:
            self.match(K.IF, K.NOT, K.EXISTS)
            f = self.match(self.database_name)
        return f

    def database_name(self):
        f = self.match(ID)
        return f

    def create_table_stmt(self):
        f = self.match(K.CREATE, K.TABLE)
        if f:
            self.match(K.IF, K.NOT, K.EXISTS)
            f = self.match(self.table_name, P('('), self.opt_table_elem_list, P(')'),
                           self.opt_interleave, self.opt_partition_by)
        return f

    def opt_table_elem_list(self):
        self.match(self.table_elem_list)
        return True

    def table_elem_list(self):
        f = self.match(self.table_elem)
        while f and self.match(P(',')):
            f = self.match(self.table_elem)
        return f

    def table_elem(self):
        f = self.match(self.column_def)
        if not f:
            f = self.match(self.table_constraint)
        if not f:
            f = self.match(self.index_def)
        # family_def not considered
        return f

    def index_def(self):
        f = self.match(K.INVERTED, K.INDEX, self.opt_name, P('('), self.index_params, P(')'))
        if not f:
            self.match(K.UNIQUE)
            f = self.match(K.INDEX, self.opt_index_name, P('('), self.index_params, P(')'),
                           self.opt_storing, self.opt_interleave)
        return f

    def opt_name(self):
        self.match(ID)
        return True

    def opt_index_name(self):
        return self.match(self.opt_name)

    def delete_stmt(self):
        pass

    def drop_stmt(self):
        pass

    def explain_stmt(self):
        pass

    def insert_stmt(self):
        pass

    def select_stmt(self):
        return self.tree([self.select_no_parens], [self.select_with_parens])

    def select_no_parens(self):
        f = self.match(self.simple_select)
        # if not f:
        #     f = self.match(self.select_with_parens)
        if f:
            f = self.match(self.sort_clause)
            if not f:
                self.match(self.opt_sort_clause, self.select_limit)
            f = True
        return f

    def select_clause(self):
        return self.tree([self.simple_select, self.select_with_parens])

    def sort_clause(self):
        f = self.match(K.ORDER, K.BY, self.sortby_list)
        return f

    def select_limit(self):
        pass

    def sortby_list(self):
        f = self.match(self.sortby)
        while f and self.match(P(',')):
            f = self.match(self.sortby)
        return f

    def sortby(self):
        f = self.match(self.a_expr, self.opt_asc_desc, self.opt_nulls_order)
        if not f:
            f = self.match(K.PRIMARY, K.KEY, ID)
            if not f:
                f = self.match(K.INDEX, ID, P('@'), ID)
            if f:
                self.match(self.opt_asc_desc)
        return f

    def opt_asc_desc(self):
        f = self.match(K.ASC)
        if f:
            print('action ASC')
        else:
            f = self.match(K.DESC)
            if f:
                print('action DESC')
        return True

    def opt_nulls_order(self):
        f = self.match(K.NULLS)
        if f:
            if self.match(K.FIRST):
                print('action NULLS FIRST')
            elif self.match(K.LAST):
                print('action NULLS LAST')
            else:
                print('error: missing NULLS ORDER')
                return False
        return True

    def select_with_parens(self):
        f = self.match(P('('), self.select_no_parens)
        if not f:
            f = self.match(P('('), self.select_with_parens)
        if f:
            f = self.match(P(')'))
        return f

    def simple_select(self):
        f = self.match(self.simple_select_clause)
        if not f:
            # f = self.match(self.set_operation)
            f = self.match(self.select_with_parens)
        if f:
            self.match(self.set_operation)
        return f

    def simple_select_clause(self):
        f = self.match(K.SELECT)
        if f:
            # a new SELECT scope
            if self._cur_act_record:
                self._act_record_l.append(self._cur_act_record)
            self._cur_act_record = ActivityRecord(self._cur_act_record)
            print('cur level =', self._cur_act_record.cur_level)

            # ALL
            if self.match(K.ALL):
                print('action all')
            # DISTINCT
            elif self.match(self.distinct_on_clause):
                print('action distinct on clause')

            elif self.match(K.DISTINCT):
                print('action distinct')

            # target list
            f = self.match(self.target_list)
            if f:
                target_l = self._sem_stack.pop()

            # from list
            if f:
                f = self.match(self.from_clause)
                if f:
                    frm_l = self._sem_stack.pop()
                    while len(frm_l) > 1:
                        op1 = frm_l.pop()
                        op2 = frm_l.pop()
                        qt = Quat('JOIN', op1, op2)
                        # print(op1.get_name(), op2.get_name())
                        frm_l.append(qt)
                        self._quat_stack.append(qt)
                    self._sem_stack.append(frm_l[0])

            if f:
                self.match(self.opt_where_clause)

                self.match(self.group_clause, self.having_clause)

            # symb check
            if not self._cur_act_record.check_symb():
                f = False
            if f:

                proj_l = []
                join_l = []
                for tar in target_l:
                    if isinstance(tar, Symbol):
                        proj_l.append(tar)
                    else:
                        # print(type(tar))
                        join_l.append(tar)
                if proj_l:
                    qt = Quat('PROJECT', proj_l, self._sem_stack.pop())
                    self._sem_stack.append(qt)
                    self._quat_stack.append(qt)
                if join_l:
                    qt = Quat('JOIN', join_l, self._sem_stack.pop())
                    self._sem_stack.append(qt)
                    self._quat_stack.append(qt)

            # end of select scope
            if self._act_record_l:
                self._cur_act_record = self._act_record_l.pop()
            else:
                self._act_record_l = None

        return f

    def distinct_on_clause(self):
        f = self.match(K.DISTINCT, K.ON, P('('), self.expr_list, P(')'))
        return f

    def expr_list(self):
        f = self.match(self.a_expr)

        expr_l = []
        while f and self.match(P(',')):
            expr_l.append(self._sem_stack.pop())
            f = self.match(self.a_expr)
        if f:
            expr_l.append(self._sem_stack.pop())
            self._sem_stack.append(expr_l)

        return f

    def a_expr(self):
        f = self.match(self.c_expr)

        if not f:
            f = self.tree([P('+')], [P('-')], [P('~')], [K.NOT])
            if f:
                f = self.match(self.a_expr)
            else:
                f = self.match(K.DEFAULT)

        if f:
            f = self.match(P('+'), self.match(self.a_expr))
            if f:
                # ADD ACTION
                qt = Quat('+', self._sem_stack.pop(), self._sem_stack.pop())
                self._sem_stack.append(qt)
                self._quat_stack.append(qt)
                return True

            else:
                f = self.match(P('-'), self.a_expr)
            if f:
                # MINUS ACTION
                qt = Quat('-', self._sem_stack.pop(), self._sem_stack.pop())
                self._sem_stack.append(qt)
                self._quat_stack.append(qt)
                return True

            else:
                f = self.match(P('*'), self.a_expr)
            if f:
                # MUL ACTION
                qt = Quat('*', self._sem_stack.pop(), self._sem_stack.pop())
                self._sem_stack.append(qt)
                self._quat_stack.append(qt)
                return True

            else:
                f = self.match(P('/'), self.a_expr)
            if f:
                # DIV ACTION
                qt = Quat('/', self._sem_stack.pop(), self._sem_stack.pop())
                self._sem_stack.append(qt)
                self._quat_stack.append(qt)
                return True

            else:
                f = self.match(P('%'), self.a_expr)
            if f:
                # MOD ACTION
                qt = Quat('%', self._sem_stack.pop(), self._sem_stack.pop())
                self._sem_stack.append(qt)
                self._quat_stack.append(qt)
                return True

            else:
                f = self.match(P('^'), self.a_expr)
            if f:
                # MINUS ACTION
                qt = Quat('^', self._sem_stack.pop(), self._sem_stack.pop())
                self._sem_stack.append(qt)
                self._quat_stack.append(qt)
                return True

            # bits operation not considered
            else:
                f = self.match(P('&'), self.a_expr)
            if not f:
                f = self.match(P('|'), self.a_expr)

            if not f:
                f = self.match(P('<'), self.a_expr)
            if f:
                # LESS THAN ACTION
                qt = Quat('<', self._sem_stack.pop(), self._sem_stack.pop())
                self._sem_stack.append(qt)
                self._quat_stack.append(qt)
                return True

            else:
                f = self.match(P('>'), self.a_expr)
            if f:
                # GREATER THAN ACTION
                qt = Quat('>', self._sem_stack.pop(), self._sem_stack.pop())
                self._sem_stack.append(qt)
                self._quat_stack.append(qt)
                return True

            else:
                f = self.match(P('='), self.a_expr)
            if f:
                # EQU ACTION
                qt = Quat('=', self._sem_stack.pop(), self._sem_stack.pop())
                self._sem_stack.append(qt)
                self._quat_stack.append(qt)
                return True

            else:
                f = self.tree([P('!='), self.a_expr], [P('<>'), self.a_expr])
            if f:
                # NOT EQU ACTION
                qt = Quat('!=', self._sem_stack.pop(), self._sem_stack.pop())
                self._sem_stack.append(qt)
                self._quat_stack.append(qt)
                return True

            else:
                f = self.match(K.AND, self.a_expr)
            if f:
                # AND ACTION
                qt = Quat('AND', self._sem_stack.pop(), self._sem_stack.pop())
                self._sem_stack.append(qt)
                self._quat_stack.append(qt)
                return True

            else:
                f = self.match(K.OR, self.a_expr)
            if f:
                # OR ACTION
                qt = Quat('OR', self._sem_stack.pop(), self._sem_stack.pop())
                self._sem_stack.append(qt)
                self._quat_stack.append(qt)
                return True

            else:
                f = self.match(K.LIKE, self.a_expr)
            if f:
                # LIKE ACTION
                qt = Quat('LIKE', self._sem_stack.pop(), self._sem_stack.pop())
                self._sem_stack.append(qt)
                self._quat_stack.append(qt)
                return True

            else:
                f = self.match(K.NOT, K.LIKE, self.a_expr)
            if f:
                # NOT LIKE ACTION
                qt = Quat('LIKE', self._sem_stack.pop(), self._sem_stack.pop())
                self._sem_stack.append(qt)
                self._quat_stack.append(qt)
                qt = Quat('NOT', self._sem_stack.pop(), None)
                self._sem_stack.append(qt)
                self._quat_stack.append(qt)
                return True

            else:
                f = self.match(K.IS, K.NULL)
            if f:
                # IS NULL ACTION
                qt = Quat('=', self._sem_stack.pop(), 'NULL')
                self._sem_stack.append(qt)
                self._quat_stack.append(qt)
                return True

            else:
                f = self.match(K.IS, K.NOT, K.NULL)
            if f:
                # NOT NULL ACTION
                qt = Quat('=', self._sem_stack.pop(), 'NULL')
                self._sem_stack.append(qt)
                self._quat_stack.append(qt)
                qt = Quat('NOT', self._sem_stack.pop(), None)
                self._sem_stack.append(qt)
                self._quat_stack.append(qt)
                return True

            else:
                f = self.match(K.IS, K.TRUE)
            if f:
                # IS TRUE ACTION
                qt = Quat('=', self._sem_stack.pop(), 'TRUE')
                self._sem_stack.append(qt)
                self._quat_stack.append(qt)
                return True

            else:
                f = self.match(K.IS, K.FALSE)
            if f:
                # IS FALSE ACTION
                qt = Quat('=', self._sem_stack.pop(), 'FALSE')
                self._sem_stack.append(qt)
                self._quat_stack.append(qt)
                return True

            else:
                f = self.match(K.IS, K.NOT, K.TRUE)
            if f:
                # IS FALSE ACTION
                qt = Quat('=', self._sem_stack.pop(), 'FALSE')
                self._sem_stack.append(qt)
                self._quat_stack.append(qt)
                return True

            else:
                f = self.match(K.IS, K.NOT, K.FALSE)
            if f:
                # IS TRUE ACTION
                qt = Quat('=', self._sem_stack.pop(), 'TRUE')
                self._sem_stack.append(qt)
                self._quat_stack.append(qt)
                return True

            else:
                f = self.match(K.BETWEEN, self.b_expr, K.AND, self.a_expr)
            if f:
                # BETWEEN ACTION
                in_l = [self._sem_stack.pop(), self._sem_stack.pop()]
                qt = Quat('IN', in_l, self._sem_stack.pop())
                self._sem_stack.append(qt)
                self._quat_stack.append(qt)
                return True

            else:
                f = self.match(K.IN, self.in_expr)
            if f:
                # IN ACTION
                qt = Quat('IN', self._sem_stack.pop(), self._sem_stack.pop())
                self._sem_stack.append(qt)
                self._quat_stack.append(qt)
                return True

            else:
                f = self.match(K.NOT, K.IN, self.in_expr)
            if f:
                # NOT IN ACTION
                op2 = self._sem_stack.pop()
                op1 = self._sem_stack.pop()
                qt = Quat('IN', op1, op2)
                self._sem_stack.append(qt)
                self._quat_stack.append(qt)
                qt = Quat('NOT', self._sem_stack.pop(), None)
                self._sem_stack.append(qt)
                self._quat_stack.append(qt)
                return True

            if not f:
                f = self.match(self.subquery_op, self.sub_type, self.a_expr)
            if not f:
                f = True
        return f

    def b_expr(self):
        f = self.match(self.c_expr)
        if not f:
            f = self.match(P('+'), self.b_expr)
            if not f:
                f = self.match(P('-'), self.b_expr)
            if not f:
                f = self.match(P('~'), self.b_expr)
        if f:
            f = self.match(P('+'), self.match(self.b_expr))
            if f:
                # ADD ACTION
                qt = Quat('+', self._sem_stack.pop(), self._sem_stack.pop())
                self._sem_stack.append(qt)
                self._quat_stack.append(qt)
                return True

            else:
                f = self.match(P('-'), self.b_expr)
            if f:
                # MINUS ACTION
                qt = Quat('-', self._sem_stack.pop(), self._sem_stack.pop())
                self._sem_stack.append(qt)
                self._quat_stack.append(qt)
                return True

            else:
                f = self.match(P('*'), self.b_expr)
            if f:
                # MUL ACTION
                qt = Quat('*', self._sem_stack.pop(), self._sem_stack.pop())
                self._sem_stack.append(qt)
                self._quat_stack.append(qt)
                return True

            else:
                f = self.match(P('/'), self.b_expr)
            if f:
                # DIV ACTION
                qt = Quat('/', self._sem_stack.pop(), self._sem_stack.pop())
                self._sem_stack.append(qt)
                self._quat_stack.append(qt)
                return True

            else:
                f = self.match(P('%'), self.b_expr)
            if f:
                # MOD ACTION
                qt = Quat('%', self._sem_stack.pop(), self._sem_stack.pop())
                self._sem_stack.append(qt)
                self._quat_stack.append(qt)
                return True

            else:
                f = self.match(P('^'), self.b_expr)
            if f:
                # POWER ACTION
                qt = Quat('^', self._sem_stack.pop(), self._sem_stack.pop())
                self._sem_stack.append(qt)
                self._quat_stack.append(qt)
                return True

            # bits operation not considered
            else:
                f = self.match(P('&'), self.b_expr)
            if not f:
                f = self.match(P('|'), self.b_expr)

            if not f:
                f = self.match(P('<'), self.b_expr)
            if f:
                # LESS THAN ACTION
                qt = Quat('<', self._sem_stack.pop(), self._sem_stack.pop())
                self._sem_stack.append(qt)
                self._quat_stack.append(qt)
                return True

            else:
                f = self.match(P('>'), self.b_expr)
            if f:
                # GREATER THAN ACTION
                qt = Quat('>', self._sem_stack.pop(), self._sem_stack.pop())
                self._sem_stack.append(qt)
                self._quat_stack.append(qt)
                return True

            else:
                f = self.match(P('='), self.b_expr)
            if f:
                # EQU ACTION
                qt = Quat('=', self._sem_stack.pop(), self._sem_stack.pop())
                self._sem_stack.append(qt)
                self._quat_stack.append(qt)
                return True

            else:
                f = self.tree([P('!='), self.b_expr], [P('<>'), self.b_expr])
            if f:
                # NOT EQU ACTION
                qt = Quat('!=', self._sem_stack.pop(), self._sem_stack.pop())
                self._sem_stack.append(qt)
                self._quat_stack.append(qt)
                return True
            else:
                f = True
        return f

    def in_expr(self):
        f = self.match(self.select_with_parens)
        if not f:
            f = self.match(self.expr_tuple1_ambiguous)
        return f

    def expr_tuple1_ambiguous(self):
        f = self.match(P('('))
        if f:
            if self.match(self.tuple1_ambiguous_values):
                print('tuple1_ambiguous_values')
            f = self.match(P(')'))
        return f

    def tuple1_ambiguous_values(self):
        f = self.match(self.a_expr)
        expr_l = []
        if f:
            if self.match(P(',')):
                if self.match(self.expr_list):
                    expr_l = self._sem_stack.pop()
            expr_l.append(self._sem_stack.pop())
            self._sem_stack.append(expr_l)
        return f

    def subquery_op(self):
        f = self.match(self.math_op)
        if not f:
            if self.match(K.NOT):
                print('action NOT')
            f = self.match(K.LIKE)
        return f

    def math_op(self):
        return self.tree([P('+')], [P('-')], [P('*')], [P('/')], [P('%')], [P('&')],
                         [P('|')], [P('^')], [P('<')], [P('>')], [P('=')], [P('<=')],
                         [P('>=')], [P('!=')], [P('<>')])

    def sub_type(self):
        return self.tree([K.ANY], [K.SOME], [K.ALL])

    def c_expr(self):
        f = self.match(self.d_expr)
        if f:
            if self.match(self.array_subscripts):
                print('action array sub')
        else:
            f = self.match(self.case_expr)
        if not f:
            f = self.match(K.EXISTS, self.select_with_parens)
            if f:
                # EXISTS ACTION
                qt = Quat('EXISTS', self._sem_stack.pop(), None)
                self._sem_stack.append(qt)
                self._quat_stack.append(qt)

        return f

    def d_expr(self):
        f = self.match(CON)
        if f:
            self._sem_stack.append(self._token_l[self._cur_pos-1].get_ref())
            return True

        else:
            f = self.match(K.TRUE)
        if f:
            self._sem_stack.append('TRUE')
            return True

        else:
            f = self.match(K.FALSE)
        if f:
            self._sem_stack.append('FALSE')
            return True

        else:
            f = self.match(K.NULL)
        if f:
            self._sem_stack.append('NULL')
            return True

        # COLUMN
        else:
            f = self.match(self.column_path_with_star)

        # not considered
        if not f:
            f = self.match(P('('), self.a_expr, P(')'))
            if f:
                if self.match(P('.')):
                    f = self.match(P('*'))
                    if not f:
                        self.match(self.unrestricted_name)
                f = True

        # FUNCTION
        if not f:
            f = self.match(self.func_expr)

        # SELECT
        if not f:
            f = self.match(self.select_with_parens)

        if not f:
            f = self.match(self.labeled_row)
        if not f:
            f = self.match(K.ARRAY)
            if f:
                f = self.match(self.select_with_parens)
                if not f:
                    f = self.match(self.row)
                if not f:
                    f = self.match(self.array_expr)
        return f

    def column_path_with_star(self):
        f = self.match(P('*'))
        if not f:
            f = self.match(ID)
            if f:
                if self.match(P('.')):
                    f = self.match(ID)
                    if f:
                        # TAB.COL
                        tab_name = self._token_l[self._cur_pos - 3].get_ref()
                        col_name = tab_name + '.' + self._token_l[self._cur_pos - 1].get_ref()

                    else:
                        f = self.match(P('*'))
                        if f:
                            # TAB.*
                            tab_name = self._token_l[self._cur_pos - 3].get_ref()
                            col_name = tab_name + '.' + '*'
                    if f:
                        if not self._cur_act_record.find_tab(tab_name):
                            self._cur_act_record.add_tab(tab_name, [])

                        t = self._cur_act_record.find_col(col_name)
                        if not t:
                            t = self._cur_act_record.add_col(col_name, [])

                        self._sem_stack.append(t)
                else:
                    # COL
                    col_name = self._token_l[self._cur_pos - 1].get_ref()
                    t = self._cur_act_record.find_col(col_name)

                    if not t:
                        t = self._cur_act_record.add_col(col_name, [])
                    self._sem_stack.append(t)

        return f

    def unrestricted_name(self):
        f = self.match(ID)
        if f:
            self._sem_stack.append(self._token_l[self._cur_pos - 1].get_ref())
        return f

    def func_expr(self):
        f = self.match(self.func_application, self.filter_clause, self.over_clause)
        if not f:
            f = self.match(self.func_expr_common_subexpr)

        return f

    def func_application(self):
        f = self.match(self.func_name, P('('))
        if f:
            if self.match(P('*')):
                print('func(*)')
            elif self.match(K.DISTINCT, self.expr_list):
                print('func(DISTINCT expr_l)')
            elif self.match(K.ALL, self.expr_list, self.opt_sort_clause):
                print('func(ALL expr_l )')
            elif self.match(self.expr_list, self.opt_sort_clause):
                print('func(expr_l)')
            f = self.match(P(')'))
        return f

    def func_name(self):
        return self.tree([K.AVG], [K.COUNT], [K.MAX], [K.MIN], [K.SUM])

    def opt_sort_clause(self):
        self.match(self.sort_clause)
        return True

    def filter_clause(self):
        self.match(K.FILTER, P('('), K.WHERE, self.a_expr, P(')'))
        return True

    def over_clause(self):
        # not considered
        self.match(K.OVER)
        return True

    def func_expr_common_subexpr(self):
        f = self.match(K.CURRENT_DATE)
        if not f:
            f = self.match(K.DATABASE)
        if not f:
            f = self.match(K.SCHEMA)
        if not f:
            f = self.match(K.ROW_COUNT)
        if not f:
            f = self.match(K.FOUND_ROWS)
        if f:
            f = self.match(P('('), P(')'))
        return f

    def labeled_row(self):
        f = self.match(self.row)
        if not f:
            f = self.match(P('('), self.row, K.AS, self.name_list, P(')'))
        return f

    def row(self):
        f = self.match(K.ROW, P('('))
        if f:
            self.match(self.expr_list)
            f = self.match(P(')'))
            return f
        f = self.match(self.expr_tuple_ambiguous)
        return f

    def expr_tuple_ambiguous(self):
        f = self.match(P('('))
        if f:
            self.match(self.tuple1_ambiguous_values)
            f = self.match(P(')'))
        return f

    def name_list(self):
        f = self.match(self.unrestricted_name)
        while f and self.match(P('(')):
            f = self.match(self.unrestricted_name)
        return f

    def array_expr(self):
        return False

    def array_subscripts(self):
        return False

    def case_expr(self):
        return False

    def target_list(self):
        f = self.match(self.target_elem)
        target_l = [self._sem_stack.pop()]

        while f and self.match(P(',')):
            f = self.match(self.target_elem)
            if f:
                target_l.append(self._sem_stack.pop())
        self._sem_stack.append(target_l)
        return f

    def target_elem(self):
        f = self.match(P('*'))

        if f:
            # *
            t = self._cur_act_record.find_col('*')
            if not t:
                t = self._cur_act_record.add_col('*', [])
            self._sem_stack.append(t)

        if not f:
            # col | const | relation with 1 row 1 column
            f = self.match(self.a_expr)

            if f:
                f = self.tree([K.AS, ID], [ID])
                if f:
                    # alias
                    alias_name = self._token_l[self._cur_pos - 1].get_ref()
                    t = self._cur_act_record.find_col(alias_name)
                    if t:
                        print('error: alias has already been existed')
                        return False
                    else:
                        # alias_ref = self._cur_act_record.last_col_ref()
                        # relation with 1 row 1 column
                        if isinstance(self._sem_stack[-1], Quat):
                            alias_ref = self._sem_stack.pop()
                        # const
                        elif isinstance(self._sem_stack[-1], str) or isinstance(self._sem_stack[-1], float):
                            alias_ref = self._sem_stack.pop()
                        # col
                        elif isinstance(self._sem_stack[-1], Symbol):
                            alias_ref = self._sem_stack.pop().get_ref()
                        t = self._cur_act_record.add_col(alias_name, alias_ref)
                    self._sem_stack.append(t)
                if not f:
                    f = True
        return f

    def from_clause(self):
        f = self.match(K.FROM)
        if f:
            f = self.match(self.from_list)
            if not f:
                return False
        return True

    def from_list(self):
        f = self.match(self.table_ref)
        if f:
            frm_l = [self._sem_stack.pop()]
            while f and self.match(P(',')):
                f = self.match(self.table_ref)
                if f:
                    frm_l.append(self._sem_stack.pop())
            if f:
                self._sem_stack.append(frm_l)
        return f

    def table_ref(self):
        f = self.match(ID)
        if f:
            tab_name = self._token_l[self._cur_pos - 1].get_ref()
            # check if is valid
            ref = None
            for tab in self._tab_l:
                if tab.get_name() == tab_name:
                    ref = tab
                    break
            if not ref:
                print('error: table {0} is not existed'.format(tab_name))
                return False
            else:
                t = self._cur_act_record.find_tab(tab_name)
                if not t:
                    t = self._cur_act_record.add_tab(tab_name, [ref])
                else:
                    t.set_ref(ref)
                self._sem_stack.append(t)

        else:
            f = self.match(self.select_with_parens)

        if not f:
            f = self.match(self.func_table)

        if f:
            self.match(self.alias_clause)

        if not f:
            f = self.match(self.joined_table)

        if not f:
            f = self.match(P('('), self.joined_table, P(')'), self.alias_clause)
        return f

    def func_table(self):
        f = self.match(self.func_expr_windowless)
        if not f:
            f = self.match(K.ROWS, K.FROM, P('('), self.rowfrom_list, P(')'))
        return f

    def func_expr_windowless(self):
        f = self.match(self.func_application)
        if not f:
            f = self.match(self.func_expr_common_subexpr)
        return f

    def rowfrom_list(self):
        f = self.match(self.rowsfrom_item)
        while f and self.match(P(',')):
            f = self.match(self.rowsfrom_item)
        return f

    def rowsfrom_item(self):
        return self.match(self.func_expr_windowless)

    def alias_clause(self):
        f = self.match(K.AS, ID)
        if not f:
            f = self.match(ID)
        if f:
            # alias
            alias_name = self._token_l[self._cur_pos - 1].get_ref()
            t = self._cur_act_record.find_col(alias_name)
            if t:
                print('error: alias has already been existed')
                return False
            else:
                # alias_ref = self._cur_act_record.last_col_ref()
                # subquery
                if isinstance(self._sem_stack[-1], Quat):
                    alias_ref = self._sem_stack.pop()
                # table
                elif isinstance(self._sem_stack[-1], Symbol):
                    alias_ref = self._sem_stack.pop().get_ref()
                else:
                    print('error: alias reference is not existed')
                    return False
                t = self._cur_act_record.add_tab(alias_name, alias_ref)
            self._sem_stack.append(t)

            # not considered
            self.match(self.name_list)
        return f

    def joined_table(self):
        f = self.match(P('('), self.joined_table, P(')'))
        if not f:
            f = self.match(self.table_ref)
            if f:
                f = self.match(K.CROSS, K.JOIN, self.table_ref)
                if not f:
                    f = self.match(K.NATURAL, self.join_type, K.JOIN, self.table_ref)
                if not f:
                    f = self.match(self.join_type, K.JOIN, self.table_ref, self.join_qual)
                if not f:
                    f = self.match(K.JOIN, self.table_ref, self.join_qual)
        return f

    def join_type(self):
        f = self.match(K.INNER)
        if not f:
            f = self.match(K.FULL)
            if not f:
                f = self.match(K.FULL)
            if not f:
                f = self.match(K.LEFT)
            if not f:
                f = self.match(K.RIGHT)
            if f:
                f = self.match(self.join_outer)
        return f

    def join_qual(self):
        f = self.match(K.ON, self.a_expr)
        if not f:
            f = self.match(K.USING, P('('), self.name_list, P(')'))
        return f

    def join_outer(self):
        f = self.match(K.OUTER)
        return True or f

    def opt_where_clause(self):
        f = self.match(self.where_clause)
        return f or True

    def where_clause(self):
        f = self.match(K.WHERE, self.a_expr)
        if f:
            qt = Quat('SELECT', self._sem_stack.pop(), self._sem_stack.pop())
            self._sem_stack.append(qt)
            self._quat_stack.append(qt)
        return f

    def group_clause(self):
        self.match(K.GROUP, K.BY, self.expr_list)
        return True

    def having_clause(self):
        self.match(K.HAVING, self.a_expr)
        return True

    def set_operation(self):
        f = self.match(K.UNION)
        if not f:
            f = self.match(K.INTERSECT)
        if not f:
            f = self.match(K.EXCEPT)
        if f:
            f = self.match(self.all_or_distinct, self.select_clause)
        return f

    def all_or_distinct(self):
        f = self.match(K.ALL)
        if not f:
            self.match(K.DISTINCT)
        return True

    def show_stmt(self):
        pass

    def update_stmt(self):
        pass

    def upset_stmt(self):
        pass

    def comment_stmt(self):
        pass


class Attribute:
    def __init__(self, name, typ):
        self._name = name
        self._type = typ

    def get_name(self):
        return self._name


class Relation:
    def __init__(self, name, col_l):
        self._name = name
        self._col_l = col_l

    def get_name(self):
        return self._name

    def get_col_l(self):
        return self._col_l


if __name__ == '__main__':
    # test = 'CREATE TABLE my_table ( id INT not null primary key, d DATE not null) INT 12'
    R1 = Relation('R1', [Attribute('x', int), Attribute('y', int), Attribute('z', str)])
    R2 = Relation('R2', [Attribute('x', int), Attribute('y', int), Attribute('t', str)])
    R3 = Relation('R3', [Attribute('x', int), Attribute('y', int)])
    # test = 'select A.x, B.y, C.* from A, B, (select * from C) where x = 2 and y > 3'
    # test = 'create table R1( id int primary key, name varchar(5), foreign key(id) references R2(id))'
    # test = 'SELECT *  FROM PARTS WHERE name = \'Wheel\' and qty > 2'
    # test = 'SELECT * FROM PARTS WHERE qty BETWEEN 20 and 50'
    # test = 'SELECT MIN(qty), MAX(qty), AVG(qty)  FROM PARTS WHERE name = \'Wheel\''
    # test = 'SELECT p_no, name, (qty * 1.2) quantity FROM PARTS'
    # test = 'SELECT department FROM EMPLOYEE WHERE department in (\'a\') GROUP BY department HAVING AVG(salary) > 400'
    # test = 'SELECT b.name  FROM  EMPLOYEE a, COLLEGE b'
    # test = ' select R1.x, (select z from R2 where y=5) from R1'
    # test = 'select y from R2 where y=5'
    # test = 'SELECT R1.x as t FROM R1 AS A, (select z from R2)'
    test = 'SELECT R1.x from R1 '
    print('--', test)
    p = Parser(test)
    p.set_schema([R1, R2, R3])
    print('main')
    if p.select_stmt() and len(p._token_l) - p._cur_pos == 0:
        print('yes')
        p.check_quat_action()
    else:
        print('no')
    print('rem -- ', len(p._token_l) - p._cur_pos)

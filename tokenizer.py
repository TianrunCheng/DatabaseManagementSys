from enum import Enum, auto
import string

"""
Definition of some constant terms
V: all valid char
S: all char accept by string (escape character not considered here)
L: letters -> a-z, A-Z
D: digits -> 0-9
NZ: nonzero -> 1-9
W: words -> 0-9, a-z, A-Z
ID: chars accepted by identifiers
WS: White Space
P: Punctuations
SP: Single Punctuations
"""
V = set(string.printable)
S = V - set('\'')
L = set(string.ascii_letters)
D = set(string.digits)
NZ = D - set('0')
W = L | D
ID = W | set('_')
WS = set(string.whitespace)
P = set(string.punctuation) - set('#')
SP = P - set('<>!|')


class TokenType(Enum):
    IDENTIFIER = auto()
    CONSTANT = auto()
    KEYWORDS = auto()
    PUNCTUATIONS = auto()

    def __str__(self):
        return self.name[0]


class Token:
    def __init__(self, token_type: TokenType, ref=None):
        self._type = token_type
        self._ref = ref

    def match(self, t):
        if not t:
            return False
        if self._type == TokenType.KEYWORDS:
            return self._ref == t
        elif self._type == TokenType.PUNCTUATIONS:
            return self._ref == t
        else:
            return t == self._type

    def get_ref(self):
        return self._ref

    def tostring(self):
        print('({0})'.format(str(self._type)))


class Keywords(Enum):
    ADD = auto()
    ALL = auto()
    ALTER = auto()
    AND = auto()
    ARRAY = auto()
    AS = auto()
    ASC = auto()
    AVG = auto()
    BETWEEN = auto()
    BOOL = auto()
    BOOLEAN = auto()
    BY = auto()
    CASCADE = auto()
    CHAR = auto()
    CHECK = auto()
    COLUMN = auto()
    CONSTRAINT = auto()
    COUNT = auto()
    COVERING = auto()
    CREATE = auto()
    CROSS = auto()
    CURRENT_DATE = auto()
    DATA = auto()
    DATABASE = auto()
    DATE = auto()
    DEFAULT = auto()
    DELETE = auto()
    DESC = auto()
    DISTINCT = auto()
    DROP = auto()
    EXCEPT = auto()
    EXISTS = auto()
    FALSE = auto()
    FILTER = auto()
    FIRST = auto()
    FLOAT = auto()
    FOREIGN = auto()
    FOUND_ROWS = auto()
    FROM = auto()
    FULL = auto()
    GROUP = auto()
    HAVING = auto()
    IF = auto()
    IN = auto()
    INDEX = auto()
    INNER = auto()
    INTERLEAVE = auto()
    INTERSECT = auto()
    IS = auto()
    INVERTED = auto()
    JOIN = auto()
    KEY = auto()
    LAST = auto()
    LEFT = auto()
    LIMIT = auto()
    INT = auto()
    LIKE = auto()
    LIST = auto()
    NATURAL = auto()
    NOT = auto()
    NOTHING = auto()
    NULL = auto()
    NULLS = auto()
    MATCH = auto()
    MAX = auto()
    MIN = auto()
    ON = auto()
    ONLY = auto()
    OR = auto()
    ORDER = auto()
    OVER = auto()
    OUTER = auto()
    PARENT = auto()
    PARTITION = auto()
    PRIMARY = auto()
    RANGE = auto()
    REFERENCES = auto()
    RENAME = auto()
    RESTRICT = auto()
    RIGHT = auto()
    ROW = auto()
    ROW_COUNT = auto()
    ROWS = auto()
    SCHEMA = auto()
    SIMPLE = auto()
    SELECT = auto()
    SET = auto()
    SORTED = auto()
    STORING = auto()
    STRING = auto()
    SUM = auto()
    TABLE = auto()
    TIME = auto()
    TO = auto()
    TRUE = auto()
    TYPE = auto()
    UNION = auto()
    UNIQUE = auto()
    UPDATE = auto()
    USING = auto()
    VALID = auto()
    VALIDATE = auto()
    VALUES = auto()
    VARCHAR = auto()
    VIEW = auto()
    WHERE = auto()

    def __str__(self):
        return str('K'+str(self.value))

    @staticmethod
    def is_keywords(t: str) -> bool:
        for k in Keywords:
            if k.name == t.upper():
                return True
        return False

    @staticmethod
    def keywords(t: str):
        for k in Keywords:
            if k.name == t.upper():
                return k
        return None


class Punctuations:

    _dict = {'<>': 0, '<=': 1, '>=': 2, '!=': 3, '||': 4}
    i = 5
    for p in P:
        _dict[p] = i
        i += 1

    def __init__(self, p: str):
        self.pun = p

    def __eq__(self, other):
        if type(self) == type(other):
            return self.pun == other.pun
        else:
            return False

    @staticmethod
    def index(t: str):
        for k, v in Punctuations._dict.items():
            if k == t:
                return v
        return None

    @staticmethod
    def is_punctuations(t: str) -> bool:
        for k, v in Punctuations._dict:
            if k == t:
                return True
        return False

    def __str__(self):
        return str('P' + str(self.index(self.pun)))


class DFA:
    def __init__(self, trans_func: dict, ignoring: set = set(), start_state: str = 's'):
        self._trans_func = trans_func
        self._ignoring = ignoring
        self._curr_state = start_state

    def getchar(self, c):
        if c in self._ignoring:
            return
        else:
            try:
                next_state = self._trans_func[self._curr_state][c]
                self._curr_state = next_state
            except KeyError:
                print('state {0} cannot deal with input {1}'.format(self._curr_state, c))

        return self

    def run(self, inputs: str):
        for i in range(len(inputs)):
            self.getchar(inputs[i])
            # print('get char {0} cur state {1}'.format(inputs[i], self._curr_state))
            if self._curr_state == '#':
                self.reset()
                # print('one token -', inputs[:i])
                return [inputs[:i], inputs[i:]]

    def reset(self):
        self._curr_state = 's'


def transit(chars: set, to: str):
    set_list = list(chars)
    to_list = len(set_list) * [to]
    paired_list = list(zip(set_list, to_list))
    return dict(paired_list)


decimal_trans_func = {
    's': {**transit(NZ, '1'), '-': '1'},
    '1': {**transit(D, '1'), '.': '2', **transit(WS | P - set('.') | set('#'), '#')},
    '2': {**transit(D, '2'), **transit(WS | P - set('.') | set('#'), '#')}
}

string_trans_func = {
    's': {'\'': '1'},
    '1': {**transit(S, '1'), '\'': '2'},
    '2': {**transit(V, '#')}
}

identifier_trans_func = {
    's': {**transit(ID, '1')},
    '1': {**transit(ID, '1'), **transit(WS | P | set('#'), '#')}
}

punctuation_trans_func = {
    's': {**transit(SP, '3'), '<': '1', '>': '2', '!': '2', '|': '4'},
    '1': {'>': '3', '=': '3', **transit(V - set('>='), '#')},
    '2': {'=': '3', **transit(V - set('='), '#')},
    '3': {**transit(V, '#')},
    '4': {'|': '3', **transit(V - set('|'), '#')}
}


class Tokenizer:
    def __init__(self):
        self.tokens_list = []
        self.identifiers_list = []
        self.constants_list = []

    def run(self, inputs: str):
        inputs += '#'
        decimal_dfa = DFA(decimal_trans_func, set())
        string_dfa = DFA(string_trans_func, set())
        identifier_dfa = DFA(identifier_trans_func, set())
        punctuation_dfa = DFA(punctuation_trans_func, set())

        while inputs:
            c = inputs[0]
            if c == '#':
                break
            # numbers
            if c in D:
                t, inputs = decimal_dfa.run(inputs)
                t = float(t)
                if t not in self.constants_list:
                    self.constants_list.append(t)
                tk = Token(TokenType.CONSTANT, t)
                self.tokens_list.append(tk)
            # string
            elif c == '\'':
                t, inputs = string_dfa.run(inputs)
                if t not in self.constants_list:
                    self.constants_list.append(t)
                tk = Token(TokenType.CONSTANT, t[1:-1])
                self.tokens_list.append(tk)
            # identifier or keyword
            elif c in ID:
                t, inputs = identifier_dfa.run(inputs)
                if Keywords.is_keywords(t):
                    tk = Token(TokenType.KEYWORDS, Keywords.keywords(t))
                else:
                    if t not in self.identifiers_list:
                        self.identifiers_list.append(t)
                    tk = Token(TokenType.IDENTIFIER, t)
                self.tokens_list.append(tk)
            # punctuation
            elif c in P:
                t, inputs = punctuation_dfa.run(inputs)
                # print('$', test_text)
                tk = Token(TokenType.PUNCTUATIONS, Punctuations(t))
                self.tokens_list.append(tk)
            elif c in WS:
                inputs = inputs[1:]
            else:
                print('error')

        return self.tokens_list

    def tostring(self):
        for tk in self.tokens_list:
            tk.tostring()


if __name__ == '__main__':
    parser = Tokenizer()
    test_text = 'int a=100 ' \
                '\n  char b =  \'b\' ' \
                'if a >= 16.34 and b = \'x\''
    print('--INPUT: {0}'.format(test_text))
    parser.run(test_text)
    parser.tostring()

    # for _ in Tokenizer().run(test_text):
    #     print('**')

    pun = Punctuations(',')
    print('$', str(pun))


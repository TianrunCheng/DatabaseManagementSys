from collections import namedtuple
from struct import pack, unpack, calcsize
from head import *
from BTrees.OOBTree import OOBTree

t = OOBTree()
t.update({1: "red", 2: "green", 3: "blue", 4: "spades"})
print(list(t.values(min=1, max=4)))

r = namedtuple('R', ['x', 'y', 'z'])
p = r(*['INT', 'STR', 'FLOAT'])


a = 'abracadabra'
s = bytes(a, 'utf-8').ljust(20)
print(s)

fmt = '?'
fmt = fmt + 'i'
print(fmt)

s = pack('i5si', *[1, b'xyz'.ljust(5), 2])
us = unpack('i5si', s)

print(us)

# print(p._asdict())
# attr_name_l = []
# attr_type_l = []
# for k, _ in p._asdict().items():
#     attr_name_l.append(k)
#     attr_type_l.append(AttrType(_).type)
#
# print(attr_type_l)


# f = open('hello', 'w')
# fileHandle = [f]
# fileHandle[0].write('1')
# fileHandle[0].close()
# fileHandle[0] = open('hello')
# s = fileHandle[0].readlines()
# print(s)
#
# bitmap = [int, True]
#
# print(bitmap)

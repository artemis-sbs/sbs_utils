


alist = [1,2,3,4]


class SpaceObjectList:
    def __init__(self, role, cycle=False):
        self.list_thing = alist[:]
        self.index = 0
        self.current = self.list_thing[0]
        self.cycle = cycle

    def __iter__(self):
        return self

    def __next__(self):
        if self.index >= len(self.list_thing) and not self.cycle:
            raise StopIteration
        self.current = self.list_thing[self.index]
        self.index+=1
        if self.index >= len(self.list_thing) and self.cycle:
            self.index=0
        return self.current

def loopy(l):
    list_thing = l[:]
    index = 0
    while True:
        yield list_thing[index]
        index+=1
        if index >= len(list_thing):
            index=0

l = SpaceObjectList(alist)
for _ in l:
    print(l.current)
    #print(next(l))

from typing import Any
from test_label import label, prev_label, python_labels
import test_label1
import test_label2

for l in python_labels:
    
    lb = python_labels[l].next_label
    if lb:
        print(f"{l} >> {lb.__name__}")
    else:
        print(l)


class RouteSpawn(object):
    def __init__(self, method, **kwargs):
        roles = kwargs.get("roles", None)
        


    def __call__(self, *args: Any, **kwds: Any) -> Any:
        print("call")



class Test:
    @RouteSpawn
    def mtest(self, so):
        pass

@RouteSpawn(roles="Roles")
def ftest(so):
    pass


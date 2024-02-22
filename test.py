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

python_labels = {}
prev_label = None

def label(func):
    global prev_label
    python_labels[func.__name__] = func
    func.next_label = None
    if prev_label is not None and prev_label.__module__ == func.__module__:
        prev_label.next_label = func
    prev_label = func


    def inner(*args, **kwargs):
        func(*args, **kwargs)
    return inner

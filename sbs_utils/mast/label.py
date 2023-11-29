# These are not the functions, but the inner decorator closure
python_labels = {}
# These are not the functions, but the inner decorator closure
next_labels = {}
prev_label = None
prev_label_module = None

# defining a decorator that can take anything
def label(*dargs, **dkwargs):
    def dec(func):
        def inner(*args, **kwargs):
            return func(*args, **kwargs)
        
        inner.func_name = func.__name__
        global prev_label
        global prev_label_module
        python_labels[func.__name__] = inner
        #
        # Make sure to restart with new modules
        #
        if prev_label is not None and prev_label_module == func.__module__:
            next_labels[prev_label] = inner
        prev_label = func.__name__
        prev_label_module = func.__module__

        return inner
    return dec

def get_fall_through(inner):
    return next_labels.get(inner.func_name, None)


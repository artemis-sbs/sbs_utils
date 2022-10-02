from sbs_utils.mast.mast import IF_EXP_REGEX, DICT_REGEX, STRING_REGEX, LIST_REGEX


print(r'((\-{2,})'+IF_EXP_REGEX+r'(\-{2,}))\n(?P<code>[\s\S]+?)\n(?P<loop>((\-{2,})|(\^{2,})))')


def export():
    def decorator(cls):
        print(f"{cls.__name__} {cls}")
        return cls
    return decorator

@export()
def test_func():
     pass

@export()
class Test():
    pass

test = Test()
test = Test()

test = Test()


test_func()
test_func()
test_func()


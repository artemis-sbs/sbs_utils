from sbs_utils.mast.mast import Mast, Scope
from sbs_utils.mast.mastrunner import MastRunner
import unittest

class TMastRunner(MastRunner):
    def runtime_error(self, message):
        print(f"RUNTIME ERROR: {message}")

def mast_compile(code=None):
    def decorator(func):
        def wrapper(self, **kargs):
            mast = Mast()
            errors = mast.compile(code)
            func(self, errors=errors, mast=mast, **kargs)
        return wrapper
    return decorator


def mast_run(code=None):
    def decorator(func):
        def wrapper(self, **kargs):
            mast = Mast()
            errors = mast.compile(code)
            runner = TMastRunner(mast)
            runner.start_thread()

            func(self, runner=runner, mast=mast, errors=errors,  **kargs)
        return wrapper
    return decorator

class TestMastCompile(unittest.TestCase):
    @mast_run( code = """
     x = 52
    -- if (x<50) --
    x=100
    -- endif --
    """)
    def test_if(self, runner, errors, mast):
        while runner.is_running():
            runner.tick()

    @mast_compile( code = """
     x = ~~[
        [2,3,4],
        [4,5,6]
        ]~~
    """)
    def test_compile_err(self, errors, mast):
        for e in errors:
            print(e)

    @mast_compile( code = """
     ~~ "{}{}".format(2,3) ~~
    """)
    def test_py_exp_compile_err(self, errors, mast):
       assert(len(errors)==0)

    # @mast_compile( code = """
    # import test/file/name.mast
    # from azip.mastlib import something.mast
    # """)
    # def test_import_compile_err(self, errors, mast):
    #    assert(len(errors)==0)

    @mast_compile( code = """
    delay 1m
    delay 2s
    delay 1m 5s
    """)
    def test_jump_compile_err(self, errors, mast):
       assert(len(errors)==0)
    @mast_compile( code = """
    ->END
    -> END
    -> a_label
    ->another
    -> maybe if x> 3
    ->> a_push
    ->>b_push
    <<-
    => fork
    f1 => fork
    =>fork_you
    =>fork_you if y == 3
    => pass_data {"self": player1, "HP": 30}
    => pass_data ~~{
        "self": player1, 
        "HP": 30
        }~~
    await => trend
    await => pass_data {"self": player1, "HP": 30}
    await => pass_data ~~{
        "self": player1, 
        "HP": 30
        }~~
    await => trend if t > 23
    """)
    def test_delay_compile_err(self, errors, mast):
       assert(len(errors)==0)


    @mast_run( code = """
    shared var1 = 100
     var2 = 200
     var3 = "This is a string"
     var4 = "This is a string {var2}"
     var5 = var1 + var2
     var6 = MastDataObject({"HP": 10, "XP": 20})
    var6.HP = 40
    # var6.HP = 400 comments
     var7 = var2 / var1 * var5
     var8 = ~~ [[2,3],[4,5]] ~~
    """)
    def test_py_exp_run_no_err(self, runner:MastRunner, errors, mast:Mast):
        assert(len(errors)==0)
        assert(runner.get_value("var1") == (100,Scope.SHARED))
        assert(runner.get_value("var2") == (200,Scope.NORMAL))
        assert(runner.get_value("var3") == ("This is a string",Scope.NORMAL))
        assert(runner.get_value("var4") == ("This is a string 200",Scope.NORMAL))
        assert(runner.get_value("var5") == (300,Scope.NORMAL))
        struct = runner.get_value("var6") 
        assert(struct[1] == Scope.NORMAL)
        assert(struct[0].HP == 40)
        assert(struct[0].XP == 20)
        assert(runner.get_value("var7")==(600, Scope.NORMAL))
        list_tup = runner.get_value("var8")
        list_value = list_tup[0]
        list_scope  = list_tup[1]
        assert(list_scope == Scope.NORMAL)
        assert(list_value[0][0]==2)
        assert(list_value[0][1]==3)
        assert(list_value[1][0]==4)
        assert(list_value[1][1]==5)


    @mast_run( code = """
    var1 = 100
    shared var2 = 100
    ->> Push  # var1 is 200 # var2 200
    ->> Push  # var1 is 300 # var2 300
    
    await => Spawn # var1 is 400 var2 is 400
    await => Spawn # var1 is 500 var2 is 500
    await => Spawn {"var1": 99} # var1 still 300 on this 
        -- if (var1==600) --
    ->> Push  # var1 is 700
    -- else --
    var1 = "Don't get here"
    -- endif --
    -- if (var1==300) --
    var1 = "Don't get here"
    -- else --
    ->> Push  # var1 is 800
    -- endif --
        -- if (var1==500) --
    var1 = "Don't get here"
    -- elif (var1==800) --
    var1 = var1+ 100
    -- else --
    var1 = "Don't get here"
    -- endif --
    ~~ print(f"VAR1 E {var1}") ~~
    ~~ print(f"VAR2 E {var2}") ~~
    

    === Push ===
    var1 = var1 + 100
    shared var2 = var2 + 100
    <<-

    === Spawn ===
    var1 = var1 + 100
    shared var2 = var2 + 100
    ->END

    """)
    def test_py_exp_run_no_err(self, runner:MastRunner, errors, mast:Mast):
        assert(len(errors)==0)
        var1 = runner.get_value("var1")
        var2 = runner.get_value("var2")
        assert(var1 == (900,Scope.NORMAL))
        assert(var2 == (800,Scope.SHARED))
        
        # run again, shared data should NOT reset
        runner.start_thread()
        var1 = runner.get_value("var1")
        var2 = runner.get_value("var2")
        assert(var1 == (900,Scope.NORMAL))
        assert(var2 == (1500,Scope.SHARED))
        
        





if __name__ == '__main__':
    try:
        unittest.main(exit=False)
    except Exception as e:
        print(e.msg)

"""
    Comment,
Label,
IfStatements,
InlineLabelStart,
InlineLabelEnd,
InlineLabelBreak,
    PyCode,
Input,
Import,
    Await,  # needs to be before Parallel
    Parallel,  # needs to be before Assign
Cancel,
    Assign,
    End,
    Jump,
    Delay,
"""

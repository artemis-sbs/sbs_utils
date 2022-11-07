from sbs_utils.mast.mast import Mast, Scope
from . import fake_sbs
import sys        
sys.modules["sbs"] = fake_sbs
from sbs_utils.mast.mastrunner import MastRunner

import unittest

Mast.enable_logging()

class TMastRunner(MastRunner):
    def runtime_error(self, message):
        print(f"RUNTIME ERROR: {message}")

def mast_compile(code=None):
        mast = Mast()
        errors = mast.compile(code)
        return (errors, mast)


def mast_run(code=None):
    mast = Mast()
    errors = mast.compile(code)
    runner = TMastRunner(mast)
    runner.start_thread()
    return (errors,runner, mast)


class TestMastCompile(unittest.TestCase):
    
    
    def test_compile_err(self):
        (errors, _) = mast_compile( code = """
x = ~~[
[2,3,4],
[4,5,6]
]~~
""")
        for e in errors:
            print(e)

    
    def test_py_exp_compile_err(self):
        (errors, mast) = mast_compile( code = """
~~ "{}{}".format(2,3) ~~
""")
        assert(len(errors)==0)

    # @mast_compile( code = """
    # import test/file/name.mast
    # from azip.mastlib import something.mast
    # """)
    # def test_import_compile_err(self, errors, mast):
    #    assert(len(errors)==0)

    
    def test_delay_compile_err(self):
        (errors, mast) = mast_compile( code = """
delay 1m
delay 2s
delay 1m 5s
""")
        assert(len(errors)==0)

    def test_loop_compile_err(self):
        (errors, mast) = mast_compile( code = """
for x while y<0:
y = y + x
next x

for x in range(10):
y = y + x
next x
""")
        assert(len(errors)==0)



    def test_jumps_compile_err(self):
        (errors, mast) =mast_compile( code = """
->END
-> END
-> a_label
->another
-> maybe if x> 3
->> a_push
->>b_push
<<-
<<- pop_jump
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

        assert(len(errors)==0)


    
    def test_py_exp_run_no_err(self):
        (errors, runner, _) = mast_run( code = """
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
     
    def test_if(self):
        (errors, runner, _) = mast_run( code = """
x = 52
if x<50:
x=100
end_if

if x<50:
x=9999
elif x>50:
x=200
else:
x=300
end_if

if x<50:
x=9999
elif x>250:
x=200
else:
x=300
end_if

    """)
        assert(len(errors)==0)
        while runner.is_running():
            runner.tick()
        x = runner.get_value("x")
        assert(x==(300, Scope.NORMAL))

    def test_match(self):
        (errors, runner, _) = mast_run( code = """
x = 52
match x:
case 50:
    x=100
    case 52:
    x=300
    case 55:
    x=999
    case _:
        x=-19
    end_match
# test the default case _
    match x:
    case 50:
    x=100
        case 55:
    x=999
    case _:
        x= x *2
    end_match
""")
        assert(len(errors)==0)
        x = runner.get_value("x")
        assert(x==(600, Scope.NORMAL))

    def test_loops(self):
            (errors, runner, _) = mast_run( code = """
    x = 52
    for y in range(10):
        x = x + 1
    next y
    x = x + 20
    x = x + 50
    for y in range(10):
        x = x + 1
    next y
    for y in range(10):
        for z in range(10):
            x = x + 1
        next z
    next y
    """)
            assert(len(errors)==0)
            x = runner.get_value("x")
            assert(x==(242, Scope.NORMAL))





    def test_py_exp_run_no_err(self):
        (errors, runner, _) = mast_run( code = """
var1 = 100
shared var2 = 100
->> Push  # var1 is 200 # var2 200
->> Push  # var1 is 300 # var2 300


await => Spawn # var1 is 400 var2 is 400
await => Spawn # var1 is 500 var2 is 500
await => Spawn {"var1": 99} # var1 still 300 on this 

if var1==600:
    ->> Push  # var1 is 700
else:
    var1 = "Don't get here"
end_if

if var1==300:
    var1 = "Don't get here"
else:
    ->> Push  # var1 is 800
end_if

if var1==500:
    var1 = "Don't get here"
elif var1 == 800:
    var1 = var1+ 100
else:
var1 = "Don't get here"
end_if


=== Push ===
var1 = var1 + 100
shared var2 = var2 + 100
<<-

=== Spawn ===
var1 = var1 + 100
shared var2 = var2 + 100
->END

    """)
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
LoopStart,
LoopEnd,
LoopBreak,
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

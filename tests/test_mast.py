from sbs_utils.mast.mast import Mast, Scope
from . import fake_sbs
import sys        
sys.modules["sbs"] = fake_sbs
from sbs_utils.mast.mastscheduler import MastScheduler

import unittest

Mast.enable_logging()

class TMastScheduler(MastScheduler):
    def runtime_error(self, message):
        print(f"RUNTIME ERROR: {message}")

def mast_compile(code=None):
        mast = Mast()
        errors = mast.compile(code)
        return (errors, mast)


def mast_run(code=None):
    mast = Mast()
    errors = mast.compile(code)
    runner = TMastScheduler(mast)
    runner.start_task()
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

    def test_import_compile_err(self):
        (errors, mast) = mast_compile( code = """
import tests/mast/imp.mast
import tests\mast\imp.mast
from tests/mast/implib.zip import imp.mast
from tests\mast\implib.zip import imp.mast
""")
        assert(len(errors)==0)
    
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
-> maybe
->> a_push
->>b_push
<<-
<<-> pop_jump
<<->> pop_push
=> fork
f1 => fork
=>fork_you
=>fork_you
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
await => trend
""")

        assert(len(errors)==0)

    def test_event_compile_err(self):
        (errors, mast) =mast_compile( code = """
event disconnect:
    log "ok"
end_event
event change_console:
    log "ok"
end_event
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
    def test_if_comp(self):
        (errors,  _) = mast_compile( code = """
x = 52
if x<50:
x=100
end_if

s = "hello"
if x=="hello":
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

    def test_await_condition(self):
        (errors, runner, _) = mast_run( code = """
shared x = 0
t => Inc
await until x==10:
    log "x={x}"
end_await
cancel t
log "done"
->END
=== Inc ==
x = x + 1
if x < 10:
    ->Inc
end_if
    """)
        assert(len(errors)==0)
        while runner.is_running():
            runner.tick()
        x = runner.get_value("x")
        assert(x==(10, Scope.SHARED))



    def test_py_exp_run_no_err(self):
        (errors, runner, _) = mast_run( code = """
var1 = 100
shared var2 = 100
->> Push  # var1 is 200 # var2 200
->> Push  # var1 is 300 # var2 300

await => Spawn # var1 is 400 var2 is 400
await => Spawn # var1 is 500 var2 is 500
await => Spawn {"var1": 99} # var1 still 500 on this 

if var1==500:
    ->> Push  # var1 is 600
else:
    var1 = 10000000
end_if

if var1==300:
    var1 = 20000000
else:
    ->> Push  # var1 is 700
end_if

if var1==500:
    var1 = 30000000
elif var1 == 700:
    var1 = var1+ 100
else:
var1 = 40000000 + var1
end_if
->END

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
        assert(var1 == (800,Scope.NORMAL))
        assert(var2 == (800,Scope.SHARED))
        
        # run again, shared data should NOT reset
        runner.start_task()
        var1 = runner.get_value("var1")
        var2 = runner.get_value("var2")
        assert(var1 == (800,Scope.NORMAL))
        assert(var2 == (1500,Scope.SHARED))
        

    def test_comments_run_no_err(self):
        (errors, runner, _) = mast_run( code = """
var1 = 100
shared var2 = 100
->> Push  # var1 is 200 # var2 200
->> Push  # var1 is 300 # var2 300

/*
->> Push  # var1 is 300 # var2 300
*/

!!!  test !!!!!!!!
await => Spawn # var1 is 400 var2 is 400
await => Spawn # var1 is 500 var2 is 500
await => Spawn {"var1": 99} # var1 still 300 on this 

if var1==600:
    ->> Push  # var1 is 700
else:
    var1 = "Don't get here"
end_if
!!! inner!!!!
if var1==300:
    var1 = "Don't get here"
else:
    ->> Push  # var1 is 800
end_if
!!! end inner !!!!

if var1==500:
    var1 = "Don't get here"
elif var1 == 800:
    var1 = var1+ 100
else:
var1 = "Don't get here"
end_if
!!!!!  end  test      !!!!!!!!!!!!!!

->END
=== Push ===
var1 = var1 + 100
shared var2 = var2 + 100
<<-
!!!s!!!!!
=== Spawn ===
var1 = var1 + 100
shared var2 = var2 + 100
->END
!!!!!!!!! end s!!!!!!
    """)
        assert(len(errors)==0)
        var1 = runner.get_value("var1")
        var2 = runner.get_value("var2")
        assert(var1 == (300,Scope.NORMAL))
        assert(var2 == (300,Scope.SHARED))

    def test_log_run_no_err(self):
                (errors, runner, _) = mast_run( code = """
    logger string output            
    -> Here
    ======== NotHere =====
    log "Got here later"
    -> End
    ======== Here =====
    log "First"
    -> NotHere
    ======== End =====
    log "Done"
    ->END
    ======== Never =====
    log "Can never reach"        
            """)
                assert(len(errors)==0)
                output = runner.get_value("output", None)
                assert(output is not None)
                st = output[0]
                #st.seek(0)
                value = st.getvalue()

                assert(value =="""First
Got here later
Done
""")


    def test_multi_log_run_no_err(self):
                (errors, runner, _) = mast_run( code = """
    logger name test1 string output1
    logger name test2 string output2
    log name test1 "Test1"
    
    log name test2 "Test2"
    log name test1 "Done1"
    log name test2 "Done2"
    
            """)
                assert(len(errors)==0)
                output = runner.get_value("output1", None)
                assert(output is not None)
                st = output[0]
                #st.seek(0)
                value = st.getvalue()
                assert(value =="""Test1\nDone1\n""")
                output = runner.get_value("output2", None)
                assert(output is not None)
                st = output[0]
                #st.seek(0)
                value = st.getvalue()
                assert(value =="""Test2\nDone2\n""")



    
    def test_log_compile_no_err(self):
                (errors, _) = mast_compile( code = """
    logger string output
    logger file "test"
    -> Here
    ======== NotHere =====
    log "Got here later"
    -> End
    ======== Here =====
    log "First"
    -> NotHere
    ======== End =====
    log "Done"
    ======== Never =====
    log "Can never reach"        
            """)
                assert(len(errors)==0)

    def test_push_pop_run_no_err(self):
                (errors, runner, _) = mast_run( code = """
    logger string output            
    ->> PushHere
    ->> PushJump
    log "out"
    ->END
    
    ======== PushHere =====
    log "Push"
    <<-
    ======== PushJump =====
    log "PushJump"
    -> Popper
    ===== Popper ====
    log "Popper"
    <<-

            """)
                assert(len(errors)==0)
                output = runner.get_value("output", None)
                assert(output is not None)
                st = output[0]
                #st.seek(0)
                value = st.getvalue()

                assert(value =="""Push
PushJump
Popper
out
""")


    def test_label_pass_through_run_no_err(self):
                (errors, runner, _) = mast_run( code = """
logger string output
======== One =====
log "One"
======== Two =====
log "Two"
===== Three ====
log "Three"
            """)
                assert(len(errors)==0)
                output = runner.get_value("output", None)
                assert(output is not None)
                st = output[0]
                #st.seek(0)
                value = st.getvalue()
                assert(value =="""One\nTwo\nThree\n""")



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

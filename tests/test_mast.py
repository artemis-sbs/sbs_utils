from sbs_utils.mast.mast import Mast, Scope
from sbs_utils.mast.mastscheduler import MastScheduler, PollResults
from sbs_utils.agent import clear_shared
from sbs_utils.mast.label import label
import unittest
# for logging
import sbs_utils.procedural.execution as ex
import sbs_utils.procedural.timers
Mast.import_python_module('sbs_utils.procedural.execution')
Mast.import_python_module('sbs_utils.procedural.timers')

def mast_assert(cond):
      assert(cond)

Mast.make_global_var("assert", mast_assert)

#Mast.enable_logging()
Mast.include_code = True

class TMastScheduler(MastScheduler):
    def runtime_error(self, message):
        print(f"RUNTIME ERROR: {message}")
        assert(False)

def mast_compile(code=None):
        mast = Mast()
        clear_shared()
        if code:
            errors = mast.compile(code, "test")
        return (errors, mast)


def mast_run(code=None, label=None):
    mast = Mast()
    clear_shared()
    errors = []
    if code:
        errors = mast.compile(code, "test")
    else:
        mast.clear("test_code")
    
    if label is None:
        label = "main"

    runner = TMastScheduler(mast)
    runner.start_task(label)
    return (errors,runner, mast)


class TestMastCompile(unittest.TestCase):
    
    
    def test_compile_err(self):
        (errors, _) = mast_compile( code = """
x = ~~[
[2,3,4],
[4,5,6]
]~~


s = ~~ ''' dfd
fsfsf
dsdds
'''~~

s = ''' dfd
fsfsf
dsdds
'''

""")
        for e in errors:
            print(e)

    
    def test_py_exp_compile_err(self):
        (errors, mast) = mast_compile( code = """
~~ "{}{}".format(2,3) ~~
~~x + fred(123)~~

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
await delay_sim(minutes=1)
await delay_test(2)
await delay_test(5,1)
await delay_test(seconds=5,minutes=1)
""")
        assert(len(errors)==0)

    def test_loop_compile_err(self):
        (errors, mast) = mast_compile( code = """
for x while y<0:
y = y + x
next x

for x while y!="test:test":
y = y + x
next x

for x in range(10):
y = y + x
next x
""")
        assert(len(errors)==0)

    def test_label_compile_err(self):
        (errors, mast) = mast_compile( code = """

    ====== test ======
    log("Hello")
    ==== test ====
    log("good bye")

""")
        assert(len(errors)==1)
        assert("duplicate label 'test'" in errors[0])

    def test_replace_label_compile(self):
        (errors, mast) = mast_compile( code = """

    ====== test ======
    log("Hello")
    ==== replace: test ====
    log("good bye")

""")
        assert(len(errors)==0)


    def test_jumps_compile_err(self):
        (errors, mast) =mast_compile( code = """


push fred {"test": 1}
->END
-> END
-> a_label
->another
-> maybe
->> a_push
->>b_push
<<-
->RETURN  if s
<<-> pop_jump
<<->> pop_push
jump fred if x==2
jump barney
if x==2:
   jump betty
end_if

if x==2:
   jump betty if x==2
end_if


""")

        assert(len(errors)==0)

    def test_jumps_run(self):
        (errors, runner, mast) =mast_run( code = """
logger(var="output")
x = 45
push test_args {"x": 2}
log("{x}")
                                         
jump fred if x==2
log("yes-1")
jump barney if x > 40
log("no-1")
->END

==== fred ===
log("no-1")
->END

==== test_args ===
log("{x}")
<<-

==== barney === 

if x==2:
    log("no-1")
   jump betty
end_if
log("yes-2")

if x==2:
   jump betty if x==45
end_if
log("yes-3")
->END

==== betty === 
log("no-1")

""")

        assert(len(errors)==0)
        output = runner.get_value("output", None)
        assert(output is not None)
        st = output[0]
        value = st.getvalue()
        assert(value=="2\n45\nyes-1\nyes-2\nyes-3\n")

    def test_await_all_any_compile_err(self):
        (errors, mast) =mast_compile( code = """

task_schedule(fork)
task_schedule(fork, {"self": player1, "HP": 30})
task_schedule(fork, data={"self": player1, "HP": 30})

~~ task_schedule(fork, data={
    "self": player1, 
    "HP": 30
    })~~
await task_schedule(thread)
await task_schedule(fork, data={"self": player1, "HP": 30})

trend = task_schedule(fork)
await trend
#await task_all(fred, barney):
    ->END
#fail:
    ->FAIL
#end_await
                                     
task_all(fred, barney)

""")

        assert(len(errors)==0)


    def test_btree_compile_err(self):
        (errors, mast) =mast_compile( code = """

yield bt sel a|b
await bt until fail seq a&b
await bt until success seq a&b
await bt invert seq a&b

yield bt sel a|b {"self": player1, "HP": 30}
await bt until fail seq a&b {"self": player1, "HP": 30}
await bt until success seq a&b {"self": player1, "HP": 30}
await bt invert seq a&b {"self": player1, "HP": 30}


yield bt sel a|b {"self": player1, "HP": 30}:
end_await

await bt until fail seq a&b {"self": player1, "HP": 30}:
end_await
await bt until success seq a&b {"self": player1, "HP": 30}:
end_await
await bt invert seq a&b {"self": player1, "HP": 30}:
end_await



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


    def test_assign(self):
        (errors, runner, _) = mast_run( code = """
x = 52
x += 10
y = 43
y-= 10
a = 23
a *= 2
b = 53
b %= 10
c = 53
c /= 10
d = 53
d //= 10
    """)
        assert(len(errors)==0)
        task = runner.active_task
        while runner.is_running():
            runner.tick()
        x = task.get_value("x", None)
        y = task.get_value("y", None)
        a = task.get_value("a", None)
        b = task.get_value("b", None)
        c = task.get_value("c", None)
        d = task.get_value("d", None)
        assert(x==(62, Scope.NORMAL))
        assert(y==(33, Scope.NORMAL))
        assert(a==(46, Scope.NORMAL))
        assert(b==(3, Scope.NORMAL))
        assert(c==(5.3, Scope.NORMAL))
        assert(d==(5, Scope.NORMAL))

    def test_assign_expect_error(self):
        (errors,  _) = mast_compile( code = """
    max = 12

    """)
        assert(len(errors)==2)
        


    def test_end_task(self):
        (errors, runner, _) = mast_run( code = """
        shared x = 0
        task_schedule(task)
        ->END
        ==== task ====
        x += 1
        ->END
    """)
        assert(len(errors)==0)
        task = runner.active_task
        while runner.is_running():
            runner.tick()
        x = task.get_value("x", None)
        assert(x==(1, Scope.SHARED))
     
    def test_if(self):
        (errors, runner, _) = mast_run( code = """
        logger(var="output")
x = 52
if x>50:
log("if-case1")
x=100
end_if

if x<50:
log("if-case2")
x=100
else:
log("else-case2")
x=100000
end_if

if x>50:
log("if-case3")
x=100
else:
log("else-case3")
x=100000
end_if

if x<50:
log("if-case4")
x=9999
elif x>50:
log("elif-case4")
x=200
else:
log("else-case4")
x=300
end_if

if x<50:
log("if-case5")
x=9999
elif x>250:
log("elif-case5")
x=200
else:
log("else-case5")
x=300
end_if
x = 52

if x > 50:
    log("if-case6")
    if x <50:
        log("inner-if-case6")
    else:
         log("inner-else-case6")
    end_if
else:
    log("else-case6")
end_if


    """)
        assert(len(errors)==0)
        task = runner.active_task
        while runner.is_running():
            runner.tick()
        output = runner.get_value("output", None)
        assert(output is not None)
        st = output[0]
        value = st.getvalue()
        assert(value=="if-case1\nelse-case2\nif-case3\nelif-case4\nelse-case5\nif-case6\ninner-else-case6\n")

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
        x = runner.active_task.get_value("x", None)
        assert(x==(600, Scope.NORMAL))

    def test_loops(self):
            (errors, runner, _) = mast_run( code = """
    logger(var="output")
    x = 52
    log("{x}")
    # 62
    for y in range(10):
        x = x + 1
    next y
    log("{x}")

    #72
    x = x + 20
    log("{x}")
    #122
    x = x + 50
    log("{x}")

    #132
    for y in range(10):
        x = x + 1
    next y
    log("{x}")
    

    #142
    count = 10
    for y while count>0:
        x = x + 1
        count = count - 1
    next y
    log("{x}")

    #147
    for y while y<5:
        x = x + 1
    next y
    log("{x}")

    #257
    for y in range(10):
        for z in range(10):
            x = x + 1
        next z
    next y
    log("{x}")

    #757
    for y in range(10):
        x = x + 500
        break
    next y
    log("{x}")

    # 757 (no adds)
    for y in range(10):
    if y > 50:
        x = x + 10000
        break
    end_if
    next y
    log("{x}")

    #777
    for y in range(10):
    x = x + 20
    if y < 5:
        break
    end_if
    next y
    log("{x}")

    #877
    for y in range(10):
    # log("877 - {y}")
    if y > 50:
        break
    end_if
    x = x + 10
    next y
    log("{x}")


    """)
            assert(len(errors)==0)
            x = runner.active_task.get_value("x", None)
            output = runner.get_value("output", None)
            assert(output is not None)
            st = output[0]
            value = st.getvalue()
            assert(x==(877, Scope.NORMAL))
    
    def test_replace_label(self):
            (errors, runner, _) = mast_run( code = """
    logger(var="output")
    -> test
    ======= test ======
    log("NO1")
    ==== replace: test ====
    log("YES1")
    ====== fred ===== 
    log("NO2")
    ==== replace: fred ====
    log("YES2")
    """)
            assert(len(errors)==0)
            output = runner.get_value("output", None)
            assert(output is not None)
            st = output[0]
            #st.seek(0)
            value = st.getvalue()
            assert(value =="""YES1\nYES2\n""")

    def test_await_condition(self):
        (errors, runner, _) = mast_run( code = """
shared x = 0
t = task_schedule(Inc)
await until x==10:
    log("x={x}")
end_await
task_cancel(t)
log("done")
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
data = MastDataObject({"var1": 100})
other = MastDataObject({"var1": 900000})
shared var2 = 100
->> Push  # var1 is 200 # var2 200
->> Push  # var1 is 300 # var2 300

await task_schedule(Spawn, data: {"data": data})  # var1 is 400 var2 is 400
await task_schedule(Spawn, data={"data": data}) # var1 is 500 var2 is 500
await task_schedule(Spawn, data={"data": other}) # var1 still 500 on this 

if data.var1==500:
    ->> Push  # var1 is 600
else:
    data.var1 = 10000000
end_if

if data.var1==300:
    data.var1 = 20000000
else:
    ->> Push  # var1 is 700
end_if

if data.var1==500:
    data.var1 = 30000000
elif data.var1 == 700:
    data.var1 = data.var1 + 100
else:
data.var1 = 40000000 + data.var1
end_if
->END

=== Push ===
data.var1 = data.var1 + 100
var2 = var2 + 100
<<-

=== Spawn ===
data.var1 = data.var1 + 100
var2 = var2 + 100
->END

    """)
        assert(len(errors)==0)
        data, scope = runner.tasks[0].get_value("data", None)
        var1 = data.var1
        var2 = runner.active_task.get_value("var2", None)
        assert(var1 == 800)
        assert(var2 == (800,Scope.SHARED))
        
        # run again, shared data should NOT reset
        task = runner.start_task()
        data, scope = runner.tasks[0].get_value("data", None)
        var1 = data.var1
        var2 = task.get_value("var2", None)
        assert(var1 == 800)
        assert(var2 == (1500,Scope.SHARED))

    def test_task_pass_data_run_no_err(self):
        (errors, runner, _) = mast_run( code = """
logger(var="output")
await task_schedule(Spawn, data= {"var1": 99})  # var1 still 500 on this 
log("after")
->END
=== Spawn ===
log("{var1}")
->END

    """)
        assert(len(errors)==0)
        while runner.tick():
            pass
        # run again, shared data should NOT reset
        output = runner.active_task.get_value("output", None)
        assert(output is not None)
        st = output[0]
        #st.seek(0)
        value = st.getvalue()
        assert(value == "99\nafter\n")
        

    def test_comments_run_no_err(self):
        (errors, runner, _) = mast_run( code = """
var1 = 100
shared var2 = 100
->> Push  # var1 is 200 # var2 200
->> Push  # var1 is 300 # var2 300

/*
->> Push  # var1 is 300 # var2 300
*/

var2 += 100

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

var2 += 100

/*
->> Push  # var1 is 300 # var2 300
*/

var2 += 100


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
        var1 = runner.active_task.get_value("var1", None)
        var2 = runner.active_task.get_value("var2", None)
        assert(var1 == (300,Scope.NORMAL))
        assert(var2 == (600,Scope.SHARED))

    def test_log_run_no_err(self):
                (errors, runner, _) = mast_run( code = """
    logger(var="output")            
    -> Here
    ======== NotHere =====
    log("Got here later")
    -> End
    ======== Here =====
    log("First")
    -> NotHere
    ======== End =====
    log("Done")
    ->END
    ======== Never =====
    log("Can never reach"        )
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
    logger(name="test1", var="output1")
    logger(name="test2", var="output2")
    log("Test1", name="test1")
    
    log("Test2", name="test2")
    log("Done1", name="test1")
    log("Done2", name="test2")
    
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
    logger(var="output")
    logger(file="test")
    -> Here
    ======== NotHere =====
    log("Got here later")
    -> End
    ======== Here =====
    log("First")
    -> NotHere
    ======== End =====
    log("Done")
    ======== Never =====
    log("Can never reach"        )
            """)
                assert(len(errors)==0)

    def test_dangle_if_compile_err(self):
                (errors, _) = mast_compile( code = """
        x = 2
        if x >3:
            print(x)
        end_if

        if x >3:
            print(x)

        if x < 5:
            print(x)

        === test == 
    
            """)
                assert(len(errors)==2)
                assert("Missing end_if" in errors[0])
                assert("Missing end_if" in errors[1])

    def test_dangle_match_compile_err(self):
                (errors, _) = mast_compile( code = """
        s = "Hello"
        match s:
            case "Hello": 

        === test == 

        match s:
            case "Hello": 

    
            """)
                assert(len(errors)==2)
                assert("Missing end_match" in errors[0])
                assert("Missing end_match" in errors[1])

    def test_dangle_await_compile_err(self):
                (errors, _) = mast_compile( code = """
        
        await my_task:
            
              

        === test == 
    
            """)
                assert(len(errors)==1)
                assert("Missing end_await" in errors[0])



    def test_dangle_loop_compile_err(self):
                (errors, _) = mast_compile( code = """
        
        for y in range(10):
            x = y + 1
            for z in range(3):
                x = x + z
              

        === test == 
    
            """)
                assert(len(errors)==2)
                assert("Missing next" in errors[0])
                assert("Missing next" in errors[1])

    def test_dangle_if2_compile_err(self):
                (errors, _) = mast_compile( code = """
        x = 2
        if x >3:
            print(x)

            """)
                assert(len(errors)==1)
                assert("Missing end_if" in errors[0])

    def test_dangle_match2_compile_err(self):
                (errors, _) = mast_compile( code = """
        s = "Hello"
        match s:
            case "Hello": 
    
            """)
                assert(len(errors)==1)
                assert("Missing end_match" in errors[0])

    def test_dangle_await2_compile_err(self):
                (errors, _) = mast_compile( code = """
        
        await my_task:
            """)
                assert(len(errors)==1)
                assert("Missing end_await" in errors[0])


    def test_dangle_loop2_compile_err(self):
                (errors, _) = mast_compile( code = """
        
        for y in range(10):
            x = y + 1
              
            """)
                assert(len(errors)==1)
                assert("Missing next" in errors[0])


    def test_push_pop_run_no_err(self):
                (errors, runner, _) = mast_run( code = """
    logger(var="output")
    ->> PushHere
    ->> PushJump
    ->> PushDouble
    log("out")
    ->END
    
    ======== PushHere =====
    log("Push")
    <<-
    ======== PushDouble =====
    log("PushDouble")
    ->> PushJump
    log("PopDouble")
    <<-

    ======== PushJump =====
    log("PushJump")
    -> Popper
    ===== Popper ====
    log("Popper")
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
PushDouble
PushJump
Popper
PopDouble
out
""")


    def test_all_no_err(self):
        (errors, runner, _) = mast_run( code = """
        logger(var="output")
        
        await task_all(Seq1, Seq2,  Seq3)
        ->END
        ======== Seq1 =====
        log("S1")
        await delay_test(3)
        log("S1 Again")
        -> END
        ======== Seq2 =====
        log("S2")
        -> END
        ===== Seq3 ====
        log("S3")
        await delay_test(1)
        log("S3 Again")
        -> END
    """)
        assert(len(errors)==0)
        for _ in range(5):
            runner.tick()
        output = runner.get_value("output", None)
        assert(output is not None)
        st = output[0]
        #st.seek(0)
        value = st.getvalue()

        assert(value =="""S1
S2
S3
S3 Again
S1 Again
""")



    def test_any_no_err(self):
        (errors, runner, _) = mast_run( code = """
        logger(var="output")
        
        await task_any(Seq1, Seq2, Seq3)
        ->END
        ======== Seq1 =====
        log("S1")
        await delay_test(20)
        log("S1 Again")
        ->FAIL
        ======== Seq2 =====
        log("S2")
        -> END
        ===== Seq3 ====
        await delay_test(20)
        log("S3")
        -> FAIL
    """)
        assert(len(errors)==0)
        for _ in range(10):
            runner.tick()
        output = runner.get_value("output", None)
        assert(output is not None)
        st = output[0]
        #st.seek(0)
        value = st.getvalue()

        assert(value =="""S1
S2
""")




    def _test_fallback_no_err(self):
        (errors, runner, _) = mast_run( code = """
        logger(var="output")
        
        await bt sel Seq1 | Seq2 | Seq3
        ->END
        ======== Seq1 =====
        log("S1")
        yield Fail
        delay test 3s
        log("S1 Again")

        ======== Seq2 =====
        log("S2")
        delay test 10s
        log("S2 Again")
        yield Success
        ===== Seq3 ====
        delay test 3s
        log("S3")
        yield faIl
    """)
        assert(len(errors)==0)
        #for _ in range(50):
        while runner.tick():
            pass
        output = runner.get_value("output", None)
        assert(output is not None)
        st = output[0]
        #st.seek(0)
        value = st.getvalue()

        assert(value =="""S1
S2
S2 Again
""")


    def _test_fallback_loop_no_err(self):
        (errors, runner, _) = mast_run( code = """
        logger(var="output")            
        shared x = 0
        === run ===
        await bt sel Seq1 | Seq2 | Seq3:
        fail:
            log("Fail")
            ->run
        end_await
        ->END
        ======== Seq1 =====
        log("S1")
        yield fail
        

        ======== Seq2 =====
        log("S2")
        x = x +1
        yield fail if x<3
        -> END
        ===== Seq3 ====
        log("S3")
        yield fail
    """)
        assert(len(errors)==0)
        #for _ in range(50):
        while runner.tick():
            pass
        output = runner.get_value("output", None)
        assert(output is not None)
        st = output[0]
        #st.seek(0)
        value = st.getvalue()

        assert(value =="""S1\nS2\nS3\nFail\nS1\nS2\nS3\nFail\nS1\nS2\n""")

    def _test_fallback_until_success_no_err(self):
        (errors, runner, _) = mast_run( code = """
        logger(var="output")            
        shared x = 0
        === run ===
        await bt until success sel Seq1 | Seq2 | Seq3
        
        ->END
        ======== Seq1 =====
        log("S1")
        yield fail
        

        ======== Seq2 =====
        log("S2")
        x = x +1
        yield fail if x<3
        -> END
        ===== Seq3 ====
        log("S3")
        yield fail
    """)
        assert(len(errors)==0)
        #for _ in range(50):
        while runner.tick():
            pass
        output = runner.get_value("output", None)
        assert(output is not None)
        st = output[0]
        #st.seek(0)
        value = st.getvalue()

        assert(value =="""S1\nS2\nS3\nS1\nS2\nS3\nS1\nS2\n""")

    def _test_fallback_no_cond_no_err(self):
        (errors, runner, _) = mast_run( code = """
        logger(var="output")            
        shared has_apple = False
        shared has_banana = False
        # Start something that will eventually find an apple
        => external
        # Start hungry until you eat something
        # await => eat_apple | eat_banana        
        await bt until success sel eat_apple | eat_banana        
        #await a
        
        log("not hungry")
        ->END
        ??????? eat_apple ??????
        ->FAIL if not has_apple
        log("Ate Apple")
        -> END
        ??????? eat_banana ?????
        -> FAIL if not has_banana
        -> END

        ===== external ====
        delay test 10s
        has_apple = True
    """)
        assert(len(errors)==0)
        #for _ in range(50):
        #    runner.tick()
        while runner.tick():
            pass
        output = runner.get_value("output", None)
        assert(output is not None)
        st = output[0]
        #st.seek(0)
        value = st.getvalue()

        assert(value =="""Ate Apple\nnot hungry\n""")



    def _test_fallback_cond_no_err(self):
        (errors, runner, _) = mast_run( code = """
        logger(var="output")

        blackboard  = ~~MastDataObject({
            "not_hungry":  False,
            "has_apple": False,
            "has_banana": False
        })~~

        #await =>=> external & not_hungry  {"blackboard": blackboard}
        task_schedule(external, data= {"blackboard": blackboard})
        await bt until success seq not_hungry {"blackboard": blackboard}
    
        
        log("not hungry")
        ->END

        ====== not_hungry =====
        #await ->=> eat_apple | eat_banana  {"blackboard": blackboard}
        yield bt sel  eat_banana | eat_apple   {"blackboard": blackboard}

        ??????? eat_apple ??????
        ->FAIL if not blackboard.has_apple
        blackboard.not_hungry = True
        log("Ate Apple")
        -> END
        ??????? eat_banana ?????
        -> FAIL if not blackboard.has_banana
        log("Ate Banana")
        blackboard.not_hungry = True
        -> END


        ===== external ====
        for x in range(10):
        #    log('fail')
            yield
        next x
        blackboard.has_apple = True
        yield success
    """)
        assert(len(errors)==0)
        for _ in range(500):
            runner.tick()
        #while runner.tick():
        #    pass
        output = runner.get_value("output", None)
        assert(output is not None)
        st = output[0]
        #st.seek(0)
        value = st.getvalue()

        assert(value =="""Ate Apple\nnot hungry\n""")



    def _test_sequence_no_err(self):
        (errors, runner, _) = mast_run( code = """
        logger(var="output")            
        
        await bt seq Seq1 & Seq2 & Seq3
        ->END
        ======== Seq1 =====
        log("S1")
        delay test 3s
        log("S1 Again")
        ->END

        ======== Seq2 =====
        log("S2")
        delay test 10s
        log("S2 Again")
        -> END
        ===== Seq3 ====
        delay test 3s
        log("S3")
        ->END
    """)
        assert(len(errors)==0)
        #for _ in range(50):
        while runner.tick():
            pass
        output = runner.get_value("output", None)
        assert(output is not None)
        st = output[0]
        #st.seek(0)
        value = st.getvalue()

        assert(value =="""S1
S1 Again
S2
S2 Again
S3
""")


    def test_label_pass_through_run_no_err(self):
                (errors, runner, _) = mast_run( code = """
logger(var="output")
======== One =====
log("One")
======== Two =====
log("Two")
===== Three ====
log("Three")
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


@label()
def try_python_one():
    ex.logger(var='output')
    x = 1
    y = 2 + x
    assert(y==3)
    ex.log(f"{y}")
    yield PollResults.OK_RUN_AGAIN
    ex.log(f"{y} again")

@label()
def try_python_two():
    x = 2
    y = 2 + x
    assert(y==4)
    ex.log(f"{y}")
    yield PollResults.OK_RUN_AGAIN
    assert(y==4)
    ex.log(f"{y} again")
    yield PollResults.OK_END
    ex.log("do not enter")
    assert(False)




class TestMastPython(unittest.TestCase):
    
    def test_python_label(self):
        (errors, runner, _) = mast_run(code=None, label=try_python_one )
        while runner.tick():
            pass
        output = runner.get_value("output", None)
        assert(output is not None)
        st = output[0]
        #st.seek(0)
        value = st.getvalue()
        assert(value =="""3\n3 again\n4\n4 again\n""")
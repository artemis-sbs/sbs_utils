import os 
s = os.environ['PYTHONPATH']
print(s)
c = os.getcwd()
print(c)

from sbs_utils.mast.mast import Mast, Scope, find_exp_end
from sbs_utils.mast.mastscheduler import MastScheduler, PollResults
from sbs_utils.agent import clear_shared
from sbs_utils.mast.label import label
import unittest
# for logging
import sbs_utils.procedural.execution as ex
import sbs_utils.procedural.timers as timers
import sbs_utils.procedural.behavior as behavior
import sbs_utils.procedural.gui as gui
import sbs_utils.procedural.signal as signal
Mast.import_python_module('sbs_utils.procedural.execution')
Mast.import_python_module('sbs_utils.procedural.behavior')
Mast.import_python_module('sbs_utils.procedural.timers')
Mast.import_python_module('sbs_utils.procedural.gui')
Mast.import_python_module('sbs_utils.procedural.signal')

from mock import sbs as sbs
from sbs_utils.helpers import FrameContext, Context, FakeEvent

def mast_assert(cond):
      assert(cond)

Mast.make_global_var("ASSERT", mast_assert)

#Mast.enable_logging()
Mast.include_code = True

class TestScoped:
    def __init__(self) -> None:
        pass
    def __enter__(self):
        FrameContext.task.set_variable("test_enter", 23)

    def __exit__(self):
        FrameContext.task.set_variable("test_exit", 34)
Mast.make_global_var("TextScoped", TestScoped)

class TMastScheduler(MastScheduler):
    def runtime_error(self, message):
        print(f"RUNTIME ERROR: {message}")
        assert(False)



def mast_compile(code=None):
        mast = Mast()
        clear_shared()
        if code:
            errors = mast.compile(code, "test", mast)
        return (errors, mast)


#FrameContext.sim= sbs.simulation()
class FakeSim:
    def __init__(self) -> None:
        self.time_tick_counter = 0
    def tick(self):
        self.time_tick_counter +=30


def mast_run(code=None, label=None):
    mast = Mast()
    clear_shared()
    errors = []
    if code:
        errors = mast.compile(code, "test2", mast)
    else:
        mast.clear("test_code")
    
    if label is None:
        label = "main"
    FrameContext.context  = Context(FakeSim(), sbs, FakeEvent())
    runner = TMastScheduler(mast)
    if len(errors)==0:
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
from tests\mast\\implib.zip import imp.mast

                                      
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


for x while y!="test:test":
    y = y + x


for x in range(10):
    y = y + x
""")
        assert(len(errors)==0)

    def test_label_compile_err(self):
        (errors, mast) = mast_compile( code = """

====== test ======
log("Hello")
==== test
log("good bye")

""")
        # Label end delimiter are now optional because we're now indention + newline based
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



->END
-> END
-> a_label
->another
-> maybe
->RETURN  if s

jump fred if x==2
jump barney
if x==2:
   jump betty


if x==2:
   jump betty if x==2
""")

        assert(len(errors)==0)


    def test_yield_compile_err(self):
        (errors, mast) =mast_compile( code = """
yield fail
yield success
yield fail if x==123
yield fail
if x==456:
   jump betty

if x==789:
   yield fail if x==200

if x==211:
   yield fail if x==222

""")

        assert(len(errors)==0)

    def test_jumps_run(self):
        (errors, runner, mast) =mast_run( code = """
logger(var="output")
x = 45
await task_schedule(test_args, data= {"x": 2})
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
yield success

==== barney === 

if x==2:
   log("no-1")
   jump betty

log("yes-2")

if x==2:
   jump betty if x==45

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
##FIX await trend
#await task_all(fred, barney):
->END
#fail:
yield fail
#end_await
                                     
task_all(fred, barney)

""")

        assert(len(errors)==0)


    def _test_btree_compile_err(self):
        (errors, mast) =mast_compile( code = """

yield bt_sel(a,b)
await bt_until_fail(bt_seq(a,b))
await bt_until_success(bt_seq(a,b))
await bt_invert(bt_seq(a,b))

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

    def test_with_statement_comp(self):
        class TestScoped:
            def __init__(self) -> None:
                self.value = 12
            def __enter__(self):
                FrameContext.task.set_variable("test_enter", 23)

            def __exit__(self):
                FrameContext.task.set_variable("test_exit", 34)
        Mast.make_global_var("TestScoped", TestScoped)

        (errors, runner, _) = mast_run( code = """
logger(var="output")
with TestScoped() as fred:
    log("{fred.value}")
log(test_enter)
log(test_exit)
""")
        assert(len(errors)==0)
        task = runner.active_task
        while runner.is_running():
            runner.tick()
        output = runner.get_value("output", None)
        assert(output is not None)
        st = output[0]
        value = st.getvalue()
        assert(value=="12\n23\n34\n")
    
    def test_assign(self):
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

=== test
# This only run the first time 
# the task runs this line
# so it will not set it to 4
# again 
default shared var_def = 4
var_def += 1
jump test if var_def < 6

svar_def = var_def
=== test2
default var_def = 4
var_def += 1
jump test2 if var_def < 6

var_inc_field = MastDataObject({"x": 10, "y": 20})
var_inc_field.x += 2

""")
        assert(len(errors)==0)
        task = runner.active_task
        while runner.is_running():
            runner.tick()
        assert(task.get_value("var1", None) == (100,Scope.SHARED))
        assert(task.get_value("var2", None) == (200,Scope.NORMAL))
        assert(task.get_value("var3", None) == ("This is a string",Scope.NORMAL))
        assert(task.get_value("var4", None) == ("This is a string 200",Scope.NORMAL))
        assert(task.get_value("var5", None) == (300,Scope.NORMAL))
        assert(task.get_value("var_def", None) == (7,Scope.SHARED))
        assert(task.get_value("svar_def", None) == (6,Scope.NORMAL))
        struct = task.get_value("var6", None) 
        assert(struct[1] == Scope.NORMAL)
        assert(struct[0].HP == 40)
        assert(struct[0].XP == 20)
        struct = task.get_value("var_inc_field", None) 
        assert(struct[1] == Scope.NORMAL)
        assert(struct[0].x == 12)
        assert(task.get_value("var7", None)==(600, Scope.NORMAL))
        list_tup = task.get_value("var8", None)
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

s = "hello"
if x=="hello":
    x=100
                                    
if x<50:
    x=9999
else:
    x=300


if x<50:
    x=9999
elif x>50:
    x=200
else:
    x=300


if x<50:
    x=9999
elif x>250:
    x=200
else:
    x=300

    """)
        assert(len(errors)==0)

    def test_if_with_on_comp(self):
        (errors,  mast) = mast_compile( code = '''
if ip_count > 0 and ctype == "helm" and not ip_timer > 0:
    on gui_message(gui_button("Infusion P-Coils")):
        print()
else:
    if ip_timer > 0:
        print()
    else:
        print()
''')
        assert(len(errors)==0)
        main = mast.labels.get('main')
        assert(main is not None)
        for cmd in main.cmds:
            print(f"{cmd.__class__} {cmd.loc} {cmd.dedent_loc}")
        
        for cmd in main.cmds[0].if_chain:
             print(cmd.loc)
        print()

    def test_if_with_on_two_comp(self):
        (errors,  mast) = mast_compile( code = '''
if ho_count > 0 and (ctype == "engineering" or ctype == "weapons"):
    on gui_message(gui_button("Haplix Overcharger")):
        print()
        if fshield > fshieldmax or rshield > rshieldmax: 
            print()
        else: 
            print()
            #for dmg in range(4):
            dmgrand = random.randrange(1,100)
            if dmgrand <= dmgcheck:
                was_damaged = grid_damage_system(ship_id, "shield")
                if was_damaged:
                    print(f"Haplix Shield Damage dmgcheck = {dmgcheck} dmgrand = {dmgrand}")
                else:
                    print(f"Haplix All Shields Damaged")
            else:
                print(f"Haplix NO Shield Damage dmgcheck = {dmgcheck} dmgrand = {dmgrand}")
            dmgcheck -= 25
        jump upgrade_screen
else:
    print()

''')
        assert(len(errors)==0)
        main = mast.labels.get('main')
        assert(main is not None)
        for cmd in main.cmds:
            print(f"{cmd.__class__} {cmd.loc}")
        
        for cmd in main.cmds[0].if_chain:
             print(cmd.loc)
        print()


    def test_assign_operators(self):
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

    def test_if_true(self):
        (errors, runner, _) = mast_run( code = """
logger(var="output")
x = 52
if x>50:
    log("if-case1")
    x=100
log("END")
""")
        assert(len(errors)==0)
        task = runner.active_task
        while runner.is_running():
            runner.tick()
        output = runner.get_value("output", None)
        assert(output is not None)
        st = output[0]
        value = st.getvalue()
        assert(value=="if-case1\nEND\n")

    def test_if_false(self):
        (errors, runner, _) = mast_run( code = """
logger(var="output")
x = 52
if x<50:
    log("if-case1")
    x=100
log("END")
""")
        assert(len(errors)==0)
        task = runner.active_task
        while runner.is_running():
            runner.tick()
        output = runner.get_value("output", None)
        assert(output is not None)
        st = output[0]
        value = st.getvalue()
        assert(value=="END\n")

    def test_if_false_else(self):
        (errors, runner, _) = mast_run( code = """
logger(var="output")
x = 52
if x<50:
    log("if-case1")
else:
    log("else-case1")
log("END")
""")
        assert(len(errors)==0)
        task = runner.active_task
        while runner.is_running():
            runner.tick()
        output = runner.get_value("output", None)
        assert(output is not None)
        st = output[0]
        value = st.getvalue()
        assert(value=="else-case1\nEND\n")

    def test_if_true_else(self):
        (errors, runner, _) = mast_run( code = """
logger(var="output")
x = 52
if x>50:
    log("if-case1")
else:
    log("else-case1")
log("END")
""")
        assert(len(errors)==0)
        task = runner.active_task
        while runner.is_running():
            runner.tick()
        output = runner.get_value("output", None)
        assert(output is not None)
        st = output[0]
        value = st.getvalue()
        assert(value=="if-case1\nEND\n")

    def test_if_if_true(self):
        (errors, runner, _) = mast_run( code = """
logger(var="output")
x = 52
if x>50:
    log("if-case1")
else:
    log("else-case1")

if x>50:
    log("if-case2")
else:
    log("else-case2")
log("END")
""")
        assert(len(errors)==0)
        task = runner.active_task
        while runner.is_running():
            runner.tick()
        output = runner.get_value("output", None)
        assert(output is not None)
        st = output[0]
        value = st.getvalue()
        assert(value=="if-case1\nif-case2\nEND\n")


    def test_if(self):
        (errors, runner, _) = mast_run( code = """
logger(var="output")
x = 52
if x>50:
    log("if-case1")
    x=100

if x<50:
    log("if-case2")
    x=100
else:
    log("else-case2")
    x=100000

if x>50:
    log("if-case3")
    x=100
else:
    log("else-case3")
    x=100000

if x<50:
    log("if-case4")
    x=9999
elif x>50:
    log("elif-case4")
    x=200
else:
    log("else-case4")
    x=300


                                       
if x<50:
    log("if-case5")
    x=9999
elif x>250:
    log("elif-case5")
    x=200
else:
    log("else-case5")
    x=300

x = 52

if x > 50:
    log("if-case6")
    if x <50:
        log("inner-if-case6")
    else:
        log("inner-else-case6")
else:
    log("else-case6")



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
    
# test the default case _
match x:
    case 50:
        x=100
    case 55:
        x=999
    case _:
        x= x *2

# test the default case _
match x:
    case 50:
        x=100
    case 55:
        x=999
    case _:
        match x:
            case 600:
                x= x *2
print("END")
""")
        assert(len(errors)==0)
        x = runner.active_task.get_value("x", None)
        assert(x==(1200, Scope.NORMAL))

    def test_loops(self):
            (errors, runner, _) = mast_run( code = """
logger(var="output")
x = 52
log("{x}")
# 62
for y in range(10):
    x = x + 1
    log("{x}")

#82
x = x + 20
log("{x}")
#132
x = x + 50
log("{x}")

#142
for y in range(10):
    x = x + 1

log("{x}")



#152
count = 10
for y while count>0:
    x = x + 1
    count = count - 1

log("{x}")


#157
for y while y<5:
    x = x + 1

log("{x}")


#257
for y in range(10):
    for z in range(10):
        x = x + 1
log("{x}")

#757
for y in range(10):
    x = x + 500
    break

log("BUT HERE{x}")

# 757 (no adds)
for y in range(10):
    if y > 50:
        x = x + 10000
        break

log("HERE {x}")

#777
for y in range(10):
    x = x + 20
    if y < 5:
        break
log("{x}")

#877
for y in range(10):
    # log("877 - {y}")
    if y > 50:
        break
    x = x + 10
    
log("{x}")


    """)
            assert(len(errors)==0)
            x = runner.active_task.get_value("x", None)
            output = runner.get_value("output", None)
            assert(output is not None)
            st = output[0]
            value = st.getvalue()
            assert(x==(877, Scope.NORMAL))

    def test_loop_for(self):
            (errors, runner, _) = mast_run( code = """
logger(var="output")
x = 52
log("{x}")
# 62
for y in range(10):
    x = x + 1
    log("{x}")

print("END")
    """)
            assert(len(errors)==0)
            x = runner.active_task.get_value("x", None)
            output = runner.get_value("output", None)
            assert(output is not None)
            st = output[0]
            value = st.getvalue()
            assert(value=="52\n53\n54\n55\n56\n57\n58\n59\n60\n61\n62\n")

    def test_loop_for_nest(self):
            (errors, runner, _) = mast_run( code = """
logger(var="output")
for y in range(2):
    log("Y{y}")
    for z in range(2):
        log("Y{y}Z{z}")
        for a in range(2):
            log("Y{y}Z{z}A{a}")
    for b in range(2):
        log("Y{y}B{b}")

log("END")
    """)
            assert(len(errors)==0)
            t = ""
            for y in range(2):
                t+= f"Y{y}\n"
                for z in range(2):
                    t+= f"Y{y}Z{z}\n"
                    for a in range(2):
                        t+= f"Y{y}Z{z}A{a}\n"
                for b in range(2):
                    t+= f"Y{y}B{b}\n"
            t+="END\n"
            output = runner.get_value("output", None)
            assert(output is not None)
            st = output[0]
            value = st.getvalue()
            assert(value==t)


    def test_loop_for_nest_continue(self):
            """
            This is testing for an edge case where the break or continue
            was the dedent on a for, which was connecting to the wrong for
            """
            (errors, runner, _) = mast_run( code = """
logger(var="output")
for y in range(3):
    log("Y{y}")
    continue if y==2
    for z in range(3):
        log("Y{y}Z{z}")
                                           
    continue if y==0
    log("+Y{y}")

log("END")
    """)
            assert(len(errors)==0)
            t = ""
            for y in range(3):
                t+= f"Y{y}\n"
                if y == 2:
                     continue
                for z in range(3):
                    t+= f"Y{y}Z{z}\n"
                if y == 0:
                     continue
                t+= f"+Y{y}\n"
            t+="END\n"
            output = runner.get_value("output", None)
            assert(output is not None)
            st = output[0]
            value = st.getvalue()
            assert(value==t)


    def test_loop_for_nest_two(self):
            (errors, runner, _) = mast_run( code = """
logger(var="output")
for y in range(2):
    log("Y{y}")
    for z in range(2):
        log("Y{y}Z{z}")
        for a in range(2):
            log("Y{y}Z{z}A{a}")
for b in range(2):
    log("B{b}")

log("END")
    """)
            assert(len(errors)==0)
            t = ""
            for y in range(2):
                t+= f"Y{y}\n"
                for z in range(2):
                    t+= f"Y{y}Z{z}\n"
                    for a in range(2):
                        t+= f"Y{y}Z{z}A{a}\n"
            for b in range(2):
                t+= f"B{b}\n"
            t+="END\n"
            output = runner.get_value("output", None)
            assert(output is not None)
            st = output[0]
            value = st.getvalue()
            assert(value==t)


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
t = task_schedule("Incr")
await  x==10:
    log("x={x}")

await delay_app(2):
    =fail:   


await delay_app(2):
    =fail:   
    

task_cancel(t)
log("done")
->END
=== Incr ==
x = x + 1
if x < 10:
    ->Incr

    """)
        assert(len(errors)==0)
        while runner.is_running():
            runner.tick()
        x = runner.get_value("x")
        assert(x==(10, Scope.SHARED))



    def test_py_exp_run_no_err(self):
        (errors, runner, _) = mast_run( code = """
logger(var="output")
shared var2 = 100

==== loop ====
data = MastDataObject({"var1": 100})
other = MastDataObject({"var1": 900000})
->> PushTest  # var1 is 200 # var2 200
log("v2 200?={var2}")
->> PushTest  # var1 is 300 # var2 300
log("v2 300?={var2}")

await task_schedule(Spawn, data={"data": data})  # var1 is 400 var2 is 400
await task_schedule(Spawn, data={"data": data}) # var1 is 500 var2 is 500
await task_schedule(Spawn, data={"data": other}) # var1 still 500 on this 
log("v2 600?={var2}")

if data.var1==500:
    ->> PushTest  # var1 is 600
else:
    data.var1 = 10000000


if data.var1==300:
    data.var1 = 20000000
else:
    ->> PushTest  # var1 is 700


if data.var1==500:
    data.var1 = 30000000
elif data.var1 == 700:
    data.var1 = data.var1 + 100
else:
    data.var1 = 40000000 + data.var1

->END

=== PushTest ===
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
        task = runner.start_task("loop")
        data, scope = runner.tasks[0].get_value("data", None)
        var1 = data.var1
        var2 = task.get_value("var2", None)
        assert(var1 == 800)

        output = runner.get_value("output", None)
        assert(output is not None)
        st = output[0]
        #st.seek(0)
        value = st.getvalue()

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

### test ###
await => Spawn # var1 is 400 var2 is 400
await => Spawn # var1 is 500 var2 is 500
await => Spawn {"var1": 99} # var1 still 300 on this 

if var1==600:
    ->> Push  # var1 is 700
else:
    var1 = "Don't get here"
end_if
### inner  ####
if var1==300:
    var1 = "Don't get here"
else:
    ->> Push  # var1 is 800
end_if
### end inner ###!

if var1==500:
    var1 = "Don't get here"
elif var1 == 800:
    var1 = var1+ 100
else:
var1 = "Don't get here"
end_if
###!!  end  test      ############!!

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
###s###!!
=== Spawn ===
var1 = var1 + 100
shared var2 = var2 + 100
->END
######### end s######
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
-> TheEnd
======== Here =====
log("First")
-> NotHere
======== TheEnd =====
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


if x >3:
    print(x)

if x < 5:
    print(x)

=== test == 

""")
                assert(len(errors)==0)
        
    def test_dangle_match_compile_err(self):
        (errors, _) = mast_compile( code = """
s = "Hello"
match s:
    case "Hello": 

=== test == 

match s:
    case "Hello": 


""")
        assert(len(errors)==0)
                

    def test_dangle_await_compile_err(self):
                (errors, _) = mast_compile( code = """
        
await my_task:
    
        

=== test == 

    """)
                assert(len(errors)==0)
                #assert("Missing end_await" in errors[0])



    def test_dangle_loop_compile_err(self):
                (errors, _) = mast_compile( code = """
        
for y in range(10):
    x = y + 1
    for z in range(3):
        x = x + z
        

=== test == 

            """)
                assert(len(errors)==0)
                #assert("Missing next" in errors[0])
                #assert("Missing next" in errors[1])

    def test_dangle_if2_compile_err(self):
                (errors, _) = mast_compile( code = """
x = 2
if x >3:
    print(x)

    """)
                assert(len(errors)==0)
                #assert("Missing end_if" in errors[0])

    def test_dangle_match2_compile_err(self):
                (errors, _) = mast_compile( code = """
s = "Hello"
match s:
    case "Hello": 

    """)
                assert(len(errors)==0)
                #assert("Missing end_match" in errors[0])

    def test_dangle_await2_compile_err(self):
                (errors, _) = mast_compile( code = """

await my_task:
    """)
                assert(len(errors)==0)
                #assert("Missing end_await" in errors[0])


    def test_dangle_loop2_compile_err(self):
                (errors, _) = mast_compile( code = """

for y in range(10):
    x = y + 1
    
""")
                assert(len(errors)==0)
                #assert("Missing next" in errors[0])


    def test_task_as_func(self):
                (errors, runner, _) = mast_run( code = """
logger(var="output")
await task_schedule(PushHere)
await task_schedule(PushJump)
await task_schedule(PushDouble)
log("out")
->END

======== PushHere =====
log("Push")
yield success

======== PushDouble =====
log("PushDouble")
await task_schedule(PushJump)
log("PopDouble")
yield success

======== PushJump =====
log("PushJump")
await task_schedule(Popper)
yield success

===== Popper ====
log("Popper")
yield success
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
                

    def test_assign_await(self):
        (errors, runner, _) = mast_run( code = """
logger(var="output")
x = await task_schedule(get_x)
y = await task_schedule(get_y)
log("{x+y=}")
->END

======== get_x =====
x = 3                                               
yield result 12 if x == 3

======== get_y =====
yield result 34

""")
        assert(len(errors)==0)
        output = runner.get_value("output", None)
        assert(output is not None)
        st = output[0]
        #st.seek(0)
        value = st.getvalue()

        assert(value =="""x+y=46\n""")


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
        
        while runner.tick():
             pass
             
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
log("Moving On")
->END
======== Seq1 =====
log("S1")
await delay_test(20)
log("S1 Again")
yield fail
======== Seq2 =====
log("S2")
-> END
===== Seq3 ====
await delay_test(20)
log("S3")
yield fail
    """)
        assert(len(errors)==0)
        while runner.tick():
             pass
        output = runner.get_value("output", None)
        assert(output is not None)
        st = output[0]
        #st.seek(0)
        value = st.getvalue()

        assert(value =="""S1\nS2\nMoving On\nS1 Again\nS3\n""")




    def test_fallback_no_err(self):
        (errors, runner, _) = mast_run( code = """
logger(var="output")

await bt_sel(Seq1, Seq2,  Seq3)
->END
======== Seq1 =====
log("S1")
yield Fail
await delay_test(3)
log("S1 Again")

======== Seq2 =====
log("S2")
await delay_test(10)
log("S2 Again")
yield Success
===== Seq3 ====
await delay_test(3)
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


    def test_fallback_loop_no_err(self):
        (errors, runner, _) = mast_run( code = """
logger(var="output")            
shared x = 0
=== run ===
await bt_sel(Seq1, Seq2,  Seq3):
    =fail:
        log("Fail")
        ->run
log("got-dedent")
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
        assert(value =="""S1\nS2\nS3\nFail\nS1\nS2\nS3\nFail\nS1\nS2\ngot-dedent\n""")

    def test_fallback_until_success_no_err(self):
        (errors, runner, _) = mast_run( code = """
logger(var="output")            
shared x = 0
=== run ===
await bt_until_success(bt_sel(Seq1, Seq2, Seq3))

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
task_schedule(external)

# Start hungry until you eat something
# await bt_sel(eat_apple | eat_banana        
# yield AWAIT(UNTIL(PollResults.BT_SUCCESS, bt_sel, (eat_apple, eat_banana, data=None))
await bt_until_success(bt_sel(eat_apple, eat_banana))
#await a

log("not hungry")
->END
??????? eat_apple ??????
yield fail if not has_apple
log("Ate Apple")
-> END
??????? eat_banana ?????
yield fail if not has_banana
-> END

===== external ====
await delay_test(seconds=10)
has_apple = True
    """)
        assert(len(errors)==0)
        
        #for _ in range(50):
        #    runner.tick()
        while runner.tick():
            FrameContext.sim.tick()

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
        yield fail if not blackboard.has_apple
        blackboard.not_hungry = True
        log("Ate Apple")
        -> END
        ??????? eat_banana ?????
        yield fail if not blackboard.has_banana
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



    def test_sequence_no_err(self):
        (errors, runner, _) = mast_run( code = """
logger(var="output")            

await bt_seq(Seq1, Seq2, Seq3)
->END
======== Seq1 =====
log("S1")
await delay_test(3)
log("S1 Again")
->END

======== Seq2 =====
log("S2")
await delay_test(10)
log("S2 Again")
-> END
===== Seq3 ====
await delay_test(3)
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

    



    def test_nested_if(self):
        (errors, mast) = mast_compile( code = """
await comms():
    + "Hail":
        comms_receive(f"Go away, {name}! You talk too much!", title_color=raider_color)
    + "Taunt":    # if enrage_value is None and not hide_taunt:
        if enrage_value:
            comms_receive(f"I'm too angry to deal with you right now, {name}.", title_color=raider_color)
        elif hide_taunt==True:
            comms_receive(f"Your taunts are worthless to us, {name}.", title_color=raider_color)
        else:
            # Navigate to sub Menu
            jump comms_taunts

    + "Surrender now" if show_surr:
        blob = to_blob(COMMS_SELECTED_ID)
        set_inventory_value(COMMS_SELECTED_ID, "surrender_count", surrender_count+1)
        shield_count = blob.get("shield_count", 0)
        s_ratio = 100
        for s in range(shield_count):
            s_max = blob.get("shield_max_val", s )
            s_cur = blob.get("shield_val", s )
            s_ratio = min(s_cur/s_max, s_ratio)

        # Secret Codecase, force surrender if active, otherwise check shield ratio
        if sc_timer > 0:
            comms_receive(f"OK we give up, {name}.", title_color=surrender_color)
            add_role(COMMS_SELECTED_ID, "surrendered")
            ~~ game_stats["ships_surrender"] += 1~~
            remove_role(COMMS_SELECTED_ID, "raider")
            sc_timer = 0
            set_inventory_value(COMMS_ORIGIN_ID, "sc_timer", sc_timer )
            set_data_set_value(COMMS_SELECTED_ID, "surrender_flag", 1)
            
        elif s_ratio < 0.09:
            if random.randint(1,6)<3:
                comms_receive(f"OK we give up, {name}.", title_color=surrender_color)
                add_role(COMMS_SELECTED_ID, "surrendered")
                ~~ game_stats["ships_surrender"] += 1~~
                remove_role(COMMS_SELECTED_ID, "raider")

                set_data_set_value(COMMS_SELECTED_ID, "surrender_flag", 1)
            else:
                comms_receive(f"We will fight to our last breath!", title_color=raider_color)
                add_role(COMMS_SELECTED_ID, "never_surrender")
        
        elif s_ratio < 0.5:
            if random.randint(0,6)<=2:
                comms_receive(f"OK we give up, {name}.", title_color=surrender_color)
                add_role(COMMS_SELECTED_ID, "surrendered")
                remove_role(COMMS_SELECTED_ID, "raider")
                set_data_set_value(COMMS_SELECTED_ID, "surrender_flag", 1)
            else:
                comms_receive(f"We can still defeat you, {name}! Prepare to die!", title_color=raider_color)

        else:
            comms_receive(f"Go climb a tree, {name}!", title_color=raider_color)

jump npc_comms
""")
        assert(len(errors)==0)
        main = mast.labels.get("main")
        l = len(main.cmds)
        for cmd in main.cmds:
             print(f"{cmd.__class__}")
        assert(l>0)

    def test_signals(self):
        (errors, runner, mast) =mast_run( code = 
"""
logger(var="output")
sub_task_schedule(listen_one)
sub_task_schedule(listen_two)
signal_emit("test_sig", {"say": "one"})
signal_emit("test_sig", {"say": "two"})

await delay_test(999)

=== listen_one 
signal_register("test_sig", respond_one)
yield idle

=== respond_one 
log("Emitted one {say}")
yield idle

=== listen_two
signal_register("test_sig", respond_two)
yield idle

=== respond_two
log("Emitted two {say}")
yield idle


""")
        assert(len(errors)==0)
        for _ in range(10):
            runner.tick()

        output = runner.get_value("output", None)
        assert(output is not None)
        st = output[0]
        value = st.getvalue()
        assert(value=="Emitted one one\nEmitted two one\nEmitted one two\nEmitted two two\n")
                

if __name__ == '__main__':
    try:
        unittest.main(exit=False)
    except Exception as e:
        print(e.msg)



class TestMastPython(unittest.TestCase):
    def test_python_label(self):
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


        (errors, runner, _) = mast_run(code=None, label=try_python_one )
        while runner.tick():
            pass
        output = runner.get_value("output", None)
        assert(output is not None)
        st = output[0]
        #st.seek(0)
        value = st.getvalue()
        assert(value =="""3\n3 again\n4\n4 again\n""")

    def test_python_await_delay(self):

        @label()
        def start():
            yield ex.task_schedule(try_python_await)
            yield ex.END()


        @label()
        def try_python_await():
            ex.logger(var='output')
            x = 1
            y = 2 + x
            assert(y==3)
            yield ex.AWAIT(timers.delay_test(2))
            ex.log(f"{y}")


        (errors, runner, _) = mast_run(code=None, label=start )
        while runner.tick():
            pass
        output = runner.get_value("output", None)
        assert(output is not None)
        st = output[0]
        #st.seek(0)
        value = st.getvalue()
        assert(value =="""3\n""")


    def test_python_jump(self):
        @label()
        def try_python_one():
            x = 1
            y = 2 + x
            assert(y==3)
            ex.log(f"{y}")
            yield ex.END()
            ex.log(f"{y} again")

        @label()
        def try_python_two():
            ex.logger(var='output')
            x = 2
            y = 2 + x
            assert(y==4)
            ex.log(f"{y}")
            yield ex.jump(try_python_one)


        (errors, runner, _) = mast_run(code=None, label=try_python_two )
        while runner.tick():
            pass
        output = runner.get_value("output", None)
        assert(output is not None)
        st = output[0]
        #st.seek(0)
        value = st.getvalue()
        assert(value =="""4\n3\n""")

    def test_python_jump_class(self):
        class Story:
            
            @label()
            def try_python_two(self):
                ex.logger(var='output')
                x = 2
                y = 2 + x
                assert(y==4)
                ex.log(f"{y}")
                yield ex.jump(self.try_python_one)
                
            @label()
            def try_python_one(self):
                x = 1
                y = 2 + x
                assert(y==3)
                ex.log(f"{y}")
                yield ex.END()
                ex.log(f"{y} again")


        story = Story()
        (errors, runner, _) = mast_run(code=None, label=story.try_python_two )
        while runner.tick():
            pass
        output = runner.get_value("output", None)
        assert(output is not None)
        st = output[0]
        #st.seek(0)
        value = st.getvalue()
        assert(value =="""4\n3\n""")

    def t_expr_parser(self, s , expected, block, valid=True):
        test = find_exp_end(s, block)

        exp = s[:test.idx]
        assert(test.idx==len(expected))
        assert(test.is_valid == valid)
        assert(exp==expected)

    def test_expr_parser(self):
        self.t_expr_parser("""hello()[""]:\nworld()""", """hello()[""]""", True)
        self.t_expr_parser("""hello(\n)["\n"\n]:\nworld()""", """hello(\n)["\n"\n]""", True)
        self.t_expr_parser("""test[1] = 1234""", """test[1] = 1234""", False)
        self.t_expr_parser("""test[1 = 1234""", """test[1 = 1234""", False, False)
        
        



    def test_sub_task(self):
        (errors, runner, mast) =mast_run( code = """
logger(var="output")
shared x = 1
===== loop ====                                          
log("preloop")
await delay_test(4)
# Don't log here timing not reliable
jump loop if x < 4
log("exit")
->END

==== sub_one ===
x += 1
log("sub_one")
yield idle

==== sub_two ===
x += 1
log("sub_two")
yield idle

==== sub_three ===
log("sub_three")
x += 1
yield END


""")

        assert(len(errors)==0)
        t = runner.active_task
        for _ in range(2):
            t.tick()
        x = t.get_variable("x")
        assert(x==1)
        st = t.start_sub_task("sub_one")
        for _ in range(2):
            t.tick()
        assert(not st.done())
        x = t.get_variable("x")
        assert(x==2)
        st.jump("sub_two")
        for _ in range(2):
            t.tick()
        assert(not t.done())
        assert(not st.done())
        
        x = t.get_variable("x")
        assert(x==3)

        st.tick()
        assert(not st.done())
        for _ in range(5):
            t.tick()
        assert(not t.done())
        assert(not st.done())
        assert(len(t.sub_tasks)==1)
        st.jump("sub_three")

        
        for _ in range(120):
            t.tick()

        x = t.get_variable("x")
        assert(x==4)    
        assert(len(t.sub_tasks)==0)
        assert(st.done())
        #assert(t.done())



        output = runner.get_value("output", None)
        assert(output is not None)
        st = output[0]
        value = st.getvalue()
        assert(t.done())
        assert(value=="preloop\nsub_one\nsub_two\nsub_three\nexit\n")

    def test_strange_for(self):
        (errors, runner, mast) =mast_run( code = """
                                         
=== test_label
my_players = [1,2,3,4]
other_loop = [1,2,3,4]
num_ids = 0
num_ids_2 = 0
for player in my_players:
    ship_id = player
    
    for friend in other_loop:
        num_ids += 1
    

    num_ids_2 += 1

print()
-> END""")
        assert(len(errors)==0)
        label = mast.labels.get("test_label")
        cmds_count = len(label.cmds)
        assert(label is not None)




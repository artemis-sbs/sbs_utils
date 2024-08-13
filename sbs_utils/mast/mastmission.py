from .mast import MastNode, DecoratorLabel, DescribableNode, Yield, IF_EXP_REGEX, STRING_REGEX_NAMED
from .pollresults import PollResults
import re


class StateMachineLabel(DecoratorLabel):
    #rule = re.compile(r'@map[ \t]+(?P<path>([\w \t]+))'+IF_EXP_REGEX)
    def __init__(self, name, if_exp=None, loc=None, compile_info=None):
        super().__init__(name, loc)
        self.description = ""
        self.if_exp = if_exp
        # need to negate if
        if self.if_exp is not None:
            self.if_exp = if_exp.strip()
            self.code = compile(self.if_exp, "<string>", "eval")

        self.next = None
        self.loc = loc
        self.replace = None
        self.cmds = []
        # This is a map of specific command type
        self.cmd_map = {}

    def can_fallthrough(self):
        return False
    
    def map_cmd(self, key, cmd):
        cmds = self.cmd_map.get(key, [])
        cmds.append(cmd)
        self.cmd_map[key] = cmds

    def test(self, task):
        #
        # The test is used by UIs etc. to find 
        # things fitting what its looking for
        # e.g. The GUI wants to display missions for fighters
        #
        if self.code is None:
            return True
        return task.eval_code(self.code)


class MissionLabel(StateMachineLabel):
    rule = re.compile(r'(@|\/\/)mission/(?P<path>[\/\w]+)[ \t]+'+STRING_REGEX_NAMED("display_name")+IF_EXP_REGEX)

    def __init__(self, path, display_name=None, q=None, if_exp=None, loc=None, compile_info=None):
        # Label stuff
        id = DecoratorLabel.next_label_id()
        name = f"mission/{path}/{id}"
        super().__init__(name, if_exp=if_exp, loc=loc)

        self.path= path
        self.display_name = display_name
        self.next = None
        self.loc = loc
        self.replace = None
        self.cmds = []

    def can_fallthrough(self):
        return True

class StateBlock(DescribableNode):
    def __init__(self):
        super().__init__()

    def is_indentable(self):
        return True



class StartBlock(StateBlock):
    rule = re.compile(r"""start:""")
    def __init__(self, is_end=None, loc=None, compile_info=None):
        super().__init__()
        self.loc = loc
        if  isinstance(compile_info.label, StateMachineLabel):
            pass
        else:
            raise Exception("start block used in unsupported label")
        compile_info.label.map_cmd("start",self)
        
    def create_end_node(self, loc, dedent_obj, compile_info):
        # End should yield success
        cmd = Yield('success', compile_info=compile_info)
        cmd.file_num = self.file_num
        cmd.line_num = self.line_num
        cmd.line = f"yield success embedded in start"
        # Dedent use to skip block inner
        self.dedent_loc = loc+1

        return cmd

class InitBlock(StateBlock):
    rule = re.compile(r"""init:""")
    def __init__(self, loc=None, compile_info=None):
        super().__init__()
        self.loc = loc
        if  isinstance(compile_info.label, StateMachineLabel):
            pass
        else:
            raise Exception("init block used in unsupported label")
        compile_info.label.map_cmd("init",self)

        
    def create_end_node(self, loc, dedent_obj, compile_info):
        # End should yield success
        cmd = Yield('success', compile_info=compile_info)
        cmd.file_num = self.file_num
        cmd.line_num = self.line_num
        cmd.line = f"yield success embedded in init"
        # Dedent use to skip block inner
        self.dedent_loc = loc+1

        return cmd



class AbortBlock(StateBlock):
    rule = re.compile(r"""abort:""")
    def __init__(self, is_end=None, loc=None, compile_info=None):
        super().__init__()
        self.loc = loc
        if  isinstance(compile_info.label, StateMachineLabel):
            pass
        else:
            raise Exception("abort block used in unsupported label")
        compile_info.label.map_cmd("abort",self)

        
    def create_end_node(self, loc, dedent_obj, compile_info):
        # End should yield success
        cmd = Yield('success', compile_info=compile_info)
        cmd.file_num = self.file_num
        cmd.line_num = self.line_num
        cmd.line = f"yield success embedded in abort"
        # Dedent use to skip block inner
        self.dedent_loc = loc+1

        return cmd

class CompleteBlock(StateBlock):
    rule = re.compile(r"""complete:""")
    def __init__(self, is_end=None, loc=None, compile_info=None):
        super().__init__()
        self.loc = loc
        if  isinstance(compile_info.label, StateMachineLabel):
            pass
        else:
            raise Exception("complete block used in unsupported label")
        compile_info.label.map_cmd("complete",self)

        
    def create_end_node(self, loc, dedent_obj, compile_info):
        # End should yield success
        cmd = Yield('success', compile_info=compile_info)
        cmd.file_num = self.file_num
        cmd.line_num = self.line_num
        cmd.line = f"yield success embedded in complete"
        # Dedent use to skip block inner
        self.dedent_loc = loc+1

        return cmd

class ObjectiveBlock(StateBlock):
    rule = re.compile(r"""objective\/(?P<name>[\/\w]+)[ \t]+"""+STRING_REGEX_NAMED("display_name")+"""[ \t]*:""")
    def __init__(self, name=None, display_name=None, q=None, loc=None, compile_info=None):
        super().__init__()
        self.loc = loc
        if  isinstance(compile_info.label, StateMachineLabel):
            pass
        else:
            raise Exception("objective block used in unsupported label")
        compile_info.label.map_cmd("objective",self)
        self.display_name = display_name
        self.name = name
        

        
    def create_end_node(self, loc, dedent_obj, compile_info):
        # End should yield fail by default
        cmd = Yield('fail', compile_info=compile_info)
        cmd.file_num = self.file_num
        cmd.line_num = self.line_num
        cmd.line = f"yield fail embedded in objective"
        # Dedent use to skip block inner
        self.dedent_loc = loc+1

        return cmd





from ..procedural.execution import task_schedule, AWAIT
from ..helpers import FrameContext


def mission_runner(label=None, data=None):
    """Runs a mission this runs the same task multiple times

    Args:
        label (_type_): a Mission Label
        data (_type_, optional): _Data to pass to the mission task. Defaults to None.

    Yields:
        PollResults: Sucess or Failure
    """
    if label is None:
        task = FrameContext.task
        label = task.get_variable("label")
        data = task.get_variable("data")

    # Run the label itself just in case
    abort_cmds = label.cmd_map.get("abort", [])
    init_cmds = label.cmd_map.get("init", [])
    start_cmds = label.cmd_map.get("start", [])
    objectives = label.cmd_map.get("objective", [])
    complete_cmd = label.cmd_map.get("complete", [])

    # run the label, gets any onchange etc.
    # it should skip the cmd block
    task = task_schedule(label, data)
    # Run the init command block
    yield AWAIT(task)
    res = task.result()

    for cmd in init_cmds:
        task.set_result(None)
        task.jump(label, cmd.loc+1)
        yield AWAIT(task)
        res = task.result()
        if res != PollResults.OK_SUCCESS:
            yield PollResults.OK_END

    # wait for the start     
    # Keep running until start, set else where
    while True:
        start = task.get_variable("__START__")
        if start:
            break
        yield PollResults.OK_RUN_AGAIN

    # Run the start command block
    for cmd in start_cmds:
        task.set_result(None)
        task.jump(label, cmd.loc+1)
        yield AWAIT(task)
        res = task.result()
        if res != PollResults.OK_SUCCESS:
            yield PollResults.OK_END

    # Continue to loop until failure or completion

    done = False
    while not done:
        # Success of an abort is end task
        for cmd in abort_cmds:
            task.set_result(None)
            task.jump(label, cmd.loc+1)
            yield AWAIT(task)
            res = task.result()
            if res == PollResults.OK_SUCCESS:
                yield PollResults.OK_END

        # Fail or success is OK
        # success means it is currently completed
        for cmd in objectives:
            task.set_result(None)
            task.jump(label, cmd.loc+1)
            yield AWAIT(task)
            res = task.result()
            if res == PollResults.OK_SUCCESS:
                pass

        done = True
        # If any fail, we're not done
        for cmd in complete_cmd:
            task.set_result(None)
            task.jump(label, cmd.loc+1)
            yield AWAIT(task)
            res = task.result()
            if res != PollResults.OK_SUCCESS:
                done = False


def mission_run(label, data= None):
    return task_schedule(mission_runner, {"label": label, "data": data})

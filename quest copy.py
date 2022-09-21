from sbs_utils.quests.quest import Quest, validate_quest, QuestRunner, PollResults, QuestRuntimeNode, Comms, Tell, Near
import os




class FakeObject:
    def __init__(self, name):
        self.name = name

class TellRunner(QuestRuntimeNode):
    def poll(self, quest, runner, node):
        print('tell {to_tag} {from_tag} "{message}"'.format(**vars(node)))
        return PollResults.OK_ADVANCE_TRUE

class CommsRunner(QuestRuntimeNode):
    def enter(self, quest, runner, node):
        self.timeout = node.minutes*60+node.seconds
        if self.timeout == 0:
            self.timeout = None
        self.tag = None

    def poll(self, quest, runner, node):

        if len(node.buttons)==0:
            # clear the comms buttons
            return PollResults.OK_ADVANCE_TRUE

        if self.timeout:
            self.timeout -= 1
            if self.timeout <= 0:
                runner.jump(node.time_jump)
                return PollResults.OK_JUMP

        return PollResults.OK_RUN_AGAIN



class NearRunner(QuestRuntimeNode):
    def enter(self, quest, runner, node):
        self.timeout = node.minutes*60+node.seconds
        self.tag = None

    def poll(self, quest, runner, node):
        # Need to check the distance

        self.timeout -= 1
        if self.timeout <= 0:
            runner.jump(node.time_jump)
            return PollResults.OK_JUMP

        return PollResults.OK_RUN_AGAIN

over =     {
        "Comms": CommsRunner,
        "Tell": TellRunner,
        "Near": CommsRunner
    }

basedir = os.path.dirname(os.path.realpath(__file__))
files = ["test.quest"]

for file in files:
    with open(os.path.join(basedir, './tests/quests', file)) as f:
        content = f.read()
        q = Quest(content)
    
        validate_quest(q)
        run = QuestRunner(q, over)
        run.start_thread(inputs={"player": FakeObject("fred"), "ship": FakeObject("wilma")})
        while not run.tick():
            pass


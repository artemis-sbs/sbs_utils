from tickdispatcher import TickDispatcher

class Objective:
    def __init__(self, shared_data):
        self.shared_data = shared_data
        self.done = False

    def begin_execute(self):
        pass

    def tick(self):
        pass

    def finish_execute(self):
        self.done = True

    def is_done(self):
        return self.done


class Sequence(Objective):
    objectives : list[Objective]
    loop: bool

    def __init(self, loop=True):
        self.loop = loop

    def add_objective(self, objective: Objective):
        self.objectives.append(objective)

    def begin_execute(self):
        self.current = 0

    def tick(self):
        cur = self.objectives[self.current]
        if (cur.is_done()):
            self.current += 1
            if self.current >= len(self.objectives):
                if self.loop:
                    self.current = 0
                else:
                    self.finish_execute()
                    
    def finish_execute(self):
        self.done = True




class BehaviorTree:
    current: Objective

    def goto(self, sim, state:State):
        self.current.leave(sim)
        self.current = state
        state.enter(sim)

class Quest(StateMachine):
    pass


class Wait(State):
    def __init__(self, delay: int):
        self.delay = delay
        self.task = None

    def enter(self, sim):
        self.task = TickDispatcher.do_once(sim, self.mark_done, self.delay)

    def leave(self, sim):
        if self.task is not None:
            self.task.stop()
            self.task = None

class Dialog(State):
    def __init__(self, source, destination):
        pass

class Choice(State):
    pass

class Reach(Objective):
    def __init__(self, source, destination):
        pass

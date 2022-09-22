from questrunner import QuestRuntimeNode, QuestRuntimeError, QuestRunner

over =     {
        "Comms": CommsRunner,
        "Tell": TellRunner,
        "Near": NearRunner,
        "Target": TargetRunner
    }

class SbsQuestRunner(QuestRunner):
    def __init__(self, quest: Quest, overrides=None):
        if overrides:
            super().__init__(quest, over|overrides)
        else:
            super().__init__(quest,  over)

    def run(self, sim, label="main", inputs=None):
        self.sim = sim
        inputs = inputs if inputs else {}
        super().start_thread( label, inputs)

    def tick(self, sim):
        self.sim = sim
        super().tick()

    def runtime_error(self, message):
        sbs.pause_sim()
        message += traceback.format_exc()
        Gui.push(self.sim, 0, ErrorPage(message))


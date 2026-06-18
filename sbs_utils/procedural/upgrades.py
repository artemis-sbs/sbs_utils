""" Manage all objective
"""
from sbs_utils.helpers import FrameContext
from sbs_utils.agent import Agent, get_story_id
from sbs_utils.procedural.query import to_set, to_object
from sbs_utils.tickdispatcher import TickDispatcher
from sbs_utils.mast.pollresults import PollResults
from sbs_utils.mast.mastscheduler import MastAsyncTask
from sbs_utils.procedural.roles import add_role, role, remove_role
from sbs_utils.procedural.links import linked_to,unlink, has_link_to, link
from sbs_utils.procedural.inventory import get_inventory_value
from sbs_utils.procedural.execution import task_schedule_server
from sbs_utils.procedural.signal import signal_emit
from sbs_utils.procedural.modifiers import modifier_remove, modifier_add



class Upgrade(Agent):
    def __init__(self, agent_id, label, data):
        self.agent_id = agent_id
        self.label = label #Label could have metadata
        self.data = data
        self.task = None
        self.id = get_story_id()
        self.add()

        # Ability to have console/client based objectives
        link(self.agent_id, "__UPGRADE__", self.id)
        self.modifiers = []

    @property
    def done(self):
        if self.task is None:
            return False
        return self.task.done
    
    @property
    def result(self):
        if self.task is None:
            return None
        return self.task.result()
    
    def discard(self):
        unlink(self.agent_id, "__UPGRADE__", self.id)
        self.remove()

    @property
    def is_active(self):
        pass
    
    def activate(self):
        UPGRADE_AGENT = to_object(self.agent_id)
        self.deactivate() # Shouldn't be active, but just n case
        if UPGRADE_AGENT is None:
            # This agent is gone
            self.discard()
        # Run the upgrade task
        data = {"UPGRADE_AGENT": UPGRADE_AGENT, "UPGRADE_AGENT_ID": self.agent_id, "UPGRADE": self}
        if self.data is not None:
            data = self.data | data

        # Task runs on the server inheriting no data except what is passed
        self.task = task_schedule_server(self.label, data, inherit=False)
        self.task.tick_in_context()
        #@signal upgrade_activated
        signal_emit("upgrade_activated", data)
        # There might be now modifiers
        # I think as long as they exists the upgrade is active

    def deactivate(self):
        # Remove all modifiers
        for m in self.modifiers:
            modifier_remove(self.agent_id, m.key, m.source)

        # Stop that task
        if not self.is_active:
            pass

        if self.task is not None:
            self.task.end()
            self.task = None 



def upgrade_add(agent_id_or_set, label, data=None, activate=False):
    """Add an upgrade to one or more agents.

    Creates an ``Upgrade`` object linked to each agent. If ``activate=True``,
    the upgrade's MAST label is scheduled immediately as a server task and the
    ``upgrade_activated`` signal is emitted.

    Args:
        agent_id_or_set (int | set | list | object): Agent ID(s) or object(s)
            to apply the upgrade to.
        label (label | str | dict): MAST label to run when the upgrade
            activates. Pass a dict with a ``"label"`` key to merge extra data:
            ``{"label": my_label, "power": 2}``.
        data (dict, optional): Variables passed to the upgrade task. Merged
            with dict-form ``label`` data. Defaults to None.
        activate (bool, optional): Activate the upgrade immediately after
            adding. Defaults to ``False``.

    Returns:
        Upgrade: The last ``Upgrade`` object created.

    Example:
        upgrade_add(SHIP_ID, shield_boost_label, activate=True)
        upgrade_add(SHIP_ID, {"label": power_label, "multiplier": 2})
    """
    # Make sure a tick task is running
    agent_id_or_set = to_set(agent_id_or_set)
    if isinstance(label, dict):
        label_data = label.copy()
        label = label_data.get("label", None)
        if label is None:
            return
        del label_data["label"]
        data = label_data | data

    for agent in agent_id_or_set:
        up = Upgrade(agent, label, data)
        if activate:
            up.activate()
    return up

def upgrade_remove_all(agent):
    """Deactivate and remove all upgrades from an agent.

    Calls ``deactivate()`` and ``discard()`` on every ``Upgrade`` linked to
    the agent, stopping their tasks and removing the ``__UPGRADE__`` links.

    Args:
        agent: Agent ID or object whose upgrades should be removed.

    Example:
        upgrade_remove_all(SHIP_ID)
    """
    by_agent = linked_to(agent, "__UPGRADE__")
    obj:Upgrade
    for obj in by_agent:
        obj.deactivate()
        obj.discard()

        


from ...helpers import FrameContext
from ...futures import Trigger
from ...mast.mast import Scope

class ClickableTrigger(Trigger):
    def __init__(self, task, name, label = None):
        self.name = name
        self.task = task
        # Needs to be set by Mast
        # Pure mast this is active Label
        # Python ith should be a callable
        self.label = label
        self.use_sub_task = False
        if label is None:
            self.label = task.active_label 
        else:
            self.use_sub_task = True
        # 0 for python the node loc of the on in Mast
        self.loc = 0
        task.main.page.add_on_click(self)

    def click(self, click_tag):
        if self.name is not None:     
            if click_tag != self.name:
                    return False
        self.task.set_value("__CLICKED__", click_tag, Scope.TEMP)
        if not self.use_sub_task:
                self.task.push_inline_block(self.label, self.loc)
                self.task.tick_in_context()
        else:
            sub_task = self.task.start_sub_task(self.label, defer=True)
            sub_task.tick_in_context()
        self.task.set_value("__CLICKED__", None, Scope.TEMP)
        
        return True

def gui_click(name_or_layout_item=None, label=None):
    """Register a click handler for a named element or layout item.

    Attaches a ``ClickableTrigger`` to the current task. When the element is
    clicked, sets ``__CLICKED__`` to the click tag and runs ``label`` inline
    (or as a sub-task if a different label is specified).

    Args:
        name_or_layout_item (str | layout object | None, optional): A click-tag
            string, a layout item exposing ``click_tag``, or ``None`` to match
            any click. Defaults to None.
        label (optional): MAST label to run on click. Defaults to the currently
            active label.

    Returns:
        ClickableTrigger: The registered trigger.

    Example:
        btn = gui_button("Fire!", on_press=None)
        gui_click(btn, on_fire_pressed)
        ///on_fire_pressed
            ~~ fire_torpedo(SHIP_ID) ~~
    """    
    task = FrameContext.task
    name = name_or_layout_item
    if name is not None:
        if not isinstance(name_or_layout_item, str):
            t_name = name_or_layout_item.click_tag
            if t_name is None:
                return 
            name = t_name
    return ClickableTrigger(task, name, label)



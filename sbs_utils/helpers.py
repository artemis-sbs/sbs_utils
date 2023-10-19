from .vec import Vec3

class Context:
    def __init__(self, sim, _sbs, _event):
        self.sim = sim
        self.sbs = _sbs
        self.event = _event


class FrameContext:
    context = None
    aspect_ratio = Vec3(1024,768,0)
    page = None
    task = None
    shared_id = -1


class FakeEvent:
    def __init__(self, client_id=0, tag="", sub_tag="", origin_id=0, selected_id=0, parent_id=0, extra_tag="", value_tag=""):
        self.tag = tag
        self.sub_tag = sub_tag
        self.client_id = client_id
        self.parent_id = parent_id
        self.origin_id = origin_id
        self.extra_tag = extra_tag
        self.value_tag = value_tag
        self.selected_id = selected_id
        self.source_point = Vec3()
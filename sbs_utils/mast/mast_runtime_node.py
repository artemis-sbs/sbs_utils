from .pollresults import PollResults

class MastRuntimeNode:
    nodes = {}
    def enter(self, mast, scheduler, node):
        pass
    def leave(self, mast, scheduler, node):
        pass
    
    def poll(self, mast, scheduler, node):
        return PollResults.OK_ADVANCE_TRUE

def mast_runtime_node(parser_node):
    def dec_args(cls):
        MastRuntimeNode.nodes[parser_node.__name__] = cls
        return cls
    return dec_args

import typing
from .agent import Agent

class LaunchDispatcher:
    _dispatch_missile = set()
    _dispatch_drone = set()

    @classmethod
    def clear(cls):
        """Drop all registered launch routes (fresh mission / in-process recompile)."""
        cls._dispatch_missile = set()
        cls._dispatch_drone = set()

    MISSILE = 0
    DRONE = 1
    
    def add_missile(cb: typing.Callable):
        LaunchDispatcher._dispatch_missile.add(cb)

    def add_drone(cb: typing.Callable):
        LaunchDispatcher._dispatch_drone.add(cb)

    def remove_missile(cb: typing.Callable):
        LaunchDispatcher._dispatch_missile.discard(cb)

    def remove_drone(cb: typing.Callable):
        LaunchDispatcher._dispatch_drone.discard(cb)

    def add_launch(launch_type, cb: typing.Callable):
        match launch_type:
            case LaunchDispatcher.MISSILE:
                LaunchDispatcher.add_missile(cb)
            case LaunchDispatcher.DRONE:
                LaunchDispatcher.add_drone(cb)

    def remove_launch(launch_type, cb: typing.Callable):
        match launch_type:
            case LaunchDispatcher.MISSILE:
                LaunchDispatcher.remove_missile(cb)
            case LaunchDispatcher.DRONE:
                LaunchDispatcher.remove_drone(cb)

    def dispatch_missile(event):
        for func in LaunchDispatcher._dispatch_missile:
            func(event)

    def dispatch_drone(event):
        for func in LaunchDispatcher._dispatch_drone:
            func(event)

    def dispatch_launch(launch_type, event):
        match launch_type:
            case LaunchDispatcher.MISSILE:
                LaunchDispatcher.dispatch_missile(event)
            case LaunchDispatcher.DRONE:
                LaunchDispatcher.dispatch_drone(event)

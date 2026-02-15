from .mast.pollresults import PollResults
import functools

class Promise:
    def __init__(self) -> None:
        self._result = None
        self._canceled = None
        self._exception = None

    def result(self):
        return self._result
    
    def rewind(self):
        # Enables any promise to with behavior trees
        pass
    
    def exception(self):
        return self._exception
    
    def set_result(self, result):
        self._result = result

    def set_exception(self, ex):
        self._exception = ex

    def done(self):
        return self._result is not None or self._canceled is not None or self._exception is not None 
    
    def poll(self):
        return PollResults.OK_RUN_AGAIN

    def canceled(self):
        return self._canceled is not None
    
    def cancel(self, msg=None):
        if self.done() or self.canceled():
            return False
        
        self._canceled = True

    def __and__(self, other):
        from .procedural.execution import promise_all, promise_any
        if isinstance(other, Promise):
            return promise_all([self, other])
        else:
            raise TypeError("Unsupported operand type(s) for & and Promise")

    def __or__(self, other):
        from .procedural.execution import promise_all, promise_any
        if isinstance(other, Promise):
            return promise_any([self, other])
        else:
            raise TypeError("Unsupported operand type(s) for & and Promise")


    


class PromiseAllAny(Promise):
    def __init__(self, proms, all) -> None:
        
        self.canceled = None
        self.exception = None
        self.all = all
        self.promises = proms
        self._result = [None for _ in range(len(self.promises))]

    def result(self):
        #
        # Return just the results in order they finished
        #
        return self._result
    
    def set_result(self, result):
        self._result = result

    def set_exception(self, ex):
        self.exception = ex

    def done(self):
        prev = self.promises
        self.promises = [None for _ in range(len(prev))]
        any_done = False
        any_left = False
        for i, p in enumerate(prev):
            if p is None:
                self.promises[i] = None
            elif p.done():
                self.promises[i] = None
                any_done = True
                self._result[i] = p.result()
            else:
                # Rebuild the promises, 
                # without the finished ones
                p.poll()
                self.promises[i] = p
                any_left = True
        is_done = any_done
        if self.all:
            is_done = not any_left

        return is_done or self.canceled is not None or self.exception is not None 
    
    def cancelled(self):
        return self.canceled is not None
    
    def cancel(self, msg=None):
        if self.done() or self.canceled:
            return False
        
        for p in self.promises:
            if p is None:
                continue
            p.cancel(msg)
        self.canceled = True

    def __and__(self, other):
        if self.all:
            self.promises.append(other)
            self._result = [None for _ in range(len(self.promises))]
            return self
        return super().__and__(other)

    def __or__(self, other):
        if not self.all:
            self.promises.append(other)
            self._result = [None for _ in range(len(self.promises))]
            return self
        return super().__or__(other)




class Waiter:
    def get_waiter(self):
        pass


class PromiseWaiter(Waiter):
    def __init__(self, promise) -> None:
        self.promise = promise
    def get_waiter(self):
        while True:
            res = self.promise.poll()
            yield res
            #yield self.promise.poll()
            if self.promise.done():
                break
        yield PollResults.OK_ADVANCE_TRUE


class AwaitBlockPromise(Promise):
    def __init__(self, timeout=None) -> None:
        super().__init__()
        # A promise from a delay function, or None
        self.timeout = timeout
        self.inlines = []
        self._initial_poll = False

    
    def initial_poll(self):
        if self._initial_poll:
            return
        self._initial_poll = True

    def poll(self):
        self.initial_poll()
        if self.timeout:
            self.timeout.poll()
            if self.timeout.done():
                self.set_result(True)
        return super().poll()


class Trigger:
    def test(self):
        pass
    def dequeue(self):
        pass


# defining a decorator that can take anything

def awaitable(func):
    @functools.wraps(func)
    def inner(*args, **kwargs):
        return func(*args, **kwargs)
    return inner



@awaitable
def promise() -> Promise:
    return Promise()

# @awaitable
# def promise_all(proms) -> PromiseAllAny:
#     return PromiseAllAny(proms, True)

# @awaitable
# def promise_any(proms) -> PromiseAllAny:
#     return PromiseAllAny(proms, False)



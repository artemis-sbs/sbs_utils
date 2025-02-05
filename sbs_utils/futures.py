from .mast.pollresults import PollResults

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

    


class PromiseAllAny(Promise):
    def __init__(self, proms, all) -> None:
        self._result = []
        self.canceled = None
        self.exception = None
        self.all = all
        self.promises = proms


    def result(self):
        #
        # Return just the results in order they finished
        #
        return [p.result() for p in self._result]
    
    def set_result(self, result):
        self._result = result

    def set_exception(self, ex):
        self.exception = ex

    def done(self):
        prev = self.promises
        self.promises = []
        for p in prev:
            if p.done():
                self._result.append(p)
            else:
                # Rebuild the promises, 
                # without the finished ones
                p.poll()
                self.promises.append(p)
        is_done = len(self._result) > 0
        if self.all:
            is_done = len(self.promises) == 0

        return is_done or self.canceled is not None or self.exception is not None 
    
    def cancelled(self):
        return self.canceled is not None
    
    def cancel(self, msg=None):
        if self.done() or self.canceled:
            return False
        
        for p in self.promises:
            p.cancel(msg)
        self.canceled = True


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


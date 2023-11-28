class Promise:
    def __init__(self) -> None:
        self._result = None
        self.canceled = None
        self.exception = None

    def _result(self):
        return self._result
    
    def set_result(self, result):
        self._result = result

    def set_exception(self, ex):
        self.exception = ex

    def done(self):
        return self._result is not None or self.canceled is not None or self.exception is not None 
    
    def cancelled(self):
        return self.canceled is not None
    
    def cancel(self, msg):
        if self.done() or self.canceled:
            return False
        
        self.canceled = True

    


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
                self.promises.append(p)
        is_done = len(self._result) > 0
        if self.all:
            is_done = len(self.promises) == 0

        return is_done or self.canceled is not None or self.exception is not None 
    
    def cancelled(self):
        return self.canceled is not None
    
    def cancel(self, msg):
        if self.done() or self.canceled:
            return False
        
        for p in self.promises:
            p.cancel(msg)
        self.canceled = True



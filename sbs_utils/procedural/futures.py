class Promise:
    def __init__(self) -> None:
        self.result = None
        self.canceled = None
        self.exception = None

    def result(self):
        return self.result
    
    def set_result(self, result):
        self.result = result

    def set_exception(self, ex):
        self.exception = ex

    def done(self):
        return self.result is not None or self.canceled is not None or self.exception is not None 
    
    def cancelled(self):
        return self.canceled is not None
    
    def cancel(self, msg):
        if self.done() or self.canceled:
            return False
        
        self.canceled = True

    
    

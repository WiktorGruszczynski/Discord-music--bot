from threading import Thread

class BetterThread(Thread):
    def __init__(self, target, args) -> None:
        Thread.__init__(self)
        #set properties
        self.value = None
        self.target = target
        self.args = args

    #function add for threading
    def run(self):
        self.value = self.target(self.args)




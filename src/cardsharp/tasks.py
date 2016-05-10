# Copyright (c) 2010 NORC
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

from __future__ import division, unicode_literals, absolute_import

__all__ = ['Task', ]

from .errors import *
from . import _handle_exception
from threading import Thread, RLock
import sys, time, inspect

class Task(object):
    def __init__(self, func, description, mark = None):
        self.description = description
        self.mark = mark
        self.func = func
        self.accept_row = len(inspect.getargspec(self.func)[0]) > 0
        self.started = False
        self.finished = False
        self._waiting = False
        
    def copy(self):
        return Task(self.func, self.description)
    
    def __enter__(self):
        return self
    
    def __exit__(self, ex_type, ex_value, ex_tb):
        return None
    
    def process(self):
        ran_once = False
        
        if not self.started:
            self.__enter__()
            self.started = True
            
        try:
            if self.accept_row:
                if self._waiting:
                    self.func(self.mark.current_row)
                    self._waiting = False
                    ran_once = True
                else:
                    while True:
                        available = self.mark.available()
                        if available == 0:
                            break
                        
                        self.mark._advance()
                        if available != None:
                            self.mark.available_rows -= 1
                        
                        self.func(self.mark.current_row)
                        self._waiting = False
                        ran_once = True                            
            else:
                while True:
                    self.func()
                    self._waiting = False
                    ran_once = True
                    
        except VoidDatasetError:
            raise
        except TaskWaiting:
            self._waiting = True
        except TaskFinished:
            self._finish()
        except:
            if not self._finish(exception = True):
                raise
            
        return ran_once
    
    def void(self):
        self.mark.void()
        self._finish()
        
    def _finish(self, exception = False):
        suppress_exception = False
        
        try:
            if self.started and not self.finished:
                if exception:
                    suppress_exception = self.__exit__(*sys.exc_info())
                else:
                    self.__exit__(None, None, None)
        
        except:
            if not exception:
                raise
        
        finally:
            self.finished = True
            self.mark.finalize()
        
        return suppress_exception
        
        
class TaskManager(object):
    def __init__(self):
        self.lock = RLock()
        self.thread = None
        
    def add_task(self, task):
        with self.lock:
            if self.thread is not None:
                with self.thread.lock:
                    if not self.thread.exiting:
                        self.thread.add_task(task)
                        return
                    
            self.thread = TaskThread()
            self.thread.add_task(task)
            self.thread.start()

class TaskThread(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.tasks = set()
        self.lock = RLock()
        self.exiting = False
        
    def add_task(self, task):
        with self.lock:
            self.tasks.add(task)
            
    def run(self):
        while True:
            with self.lock:
                tasks = set(self.tasks)
               
            ran_once = False 
            for task in tasks:
                try:
                    ran_once = task.process() or ran_once
                except:
                    task.void()
                    _handle_exception(*sys.exc_info())

                if task.finished:
                    self.tasks.remove(task)
            
            with self.lock:
                if not self.tasks:
                    self.exiting = True
                    return
                
            if not ran_once:
                try:
                    time.sleep(0.25)    
                except:
                    pass

task_manager = TaskManager()

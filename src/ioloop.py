#!/usr/local/bin/python3
# -*- coding: utf-8 -*-
# Filename: ioloop.py
# Author:   Chenbin
# Time-stamp: <2014-06-18 Wed 17:03:01>

import threading
import functools

from util import Configurable

class IOLoop(Configurable):
    # Constants from the epoll module
    _EPOLLIN = 0x001
    _EPOLLPRI = 0x002
    _EPOLLOUT = 0x004
    _EPOLLERR = 0x008
    _EPOLLHUP = 0x010
    _EPOLLRDHUP = 0x2000
    _EPOLLONESHOT = (1 << 30)
    _EPOLLET = (1 << 31)
                                        
    READ = _EPOLLIN
    WRITE = _EPOLLOUT
    ERROR = _EPOLLERR | _EPOLLHUP

    _instance_lock = threading.Lock()
    _current = threading.local()

    @staticmethod
    def instance():
        if not hasattr(IOLoop, '_instance'):
            with IOLoop._instance_lock:
                if not hasattr(IOLoop, '_instance'):
                    IOLoop._instance = IOLoop()
        return IOLoop._instance

    @staticmethod
    def current():
        current = getattr(IOLoop._current, 'instance', None)
        if current is None:
            return IOLoop.instance()
        return current

    @classmethod
    def configurable_base(cls):
        return IOLoop

    @classmethod
    def configurable_default(cls):
        from epoll import EPollIOLoop
        return EPollIOLoop

    def add_handler(self, fd, handler, events):
        raise NotImplementedError()

    def update_handler(self, fd, events):
        raise NotImplementedError()
    
    def remove_handler(self, fd):
        raise NotImplementedError()

    def add_callback(self, callback, *args, **kwargs):
        raise NotImplementedError()

    def start(self):
        raise NotImplementedError()


_POLL_TIMEOUT = 3600.0

class PollIOLoop(IOLoop):
    def initialize(self, impl):
        self._impl = impl
        self._events = {}
        self._handlers = {}
        self._callbacks = []
        self._callback_lock = threading.Lock()

    def add_handler(self, fd, handler, events):
        self._handlers[fd] = handler
        self._impl.register(fd, events | self.ERROR)

    def update_handler(self, fd, events):
        self._impl.modify(fd, events | self.ERROR)

    def remove_handler(self, fd):
        self._handlers.pop(fd, None)
        self._events.pop(fd, None)
        try:
            self._impl.unregister(fd)
        except Exception as e:
            print("error delete fd from ioloop...", e)

    def add_callback(self, callback, *args, **kwargs):
        with self._callback_lock:
            self._callbacks.append(functools.partial(callback, *args, **kwargs))

    def _run_callback(self, callback):
        try:
            callback()
        except:
            print('callback error')

    def start(self):        
        old_current = getattr(IOLoop._current, 'instance', None)
        IOLoop._current.instance = self
        try:
            while True:
                poll_timeout = _POLL_TIMEOUT
                with self._callback_lock:
                    callbacks = self._callbacks
                    self._callbacks = []
                for callback in callbacks:
                    self._run_callback(callback)

               # self._run_callback may add callback again,
               # set timeout to 0, run callback again
                if self._callbacks:
                    poll_timeout = 0.0
                
                try:
                    event_pairs = self._impl.poll(poll_timeout)
                except Exception as e:
                    print('error: ', e)
                    break

                self._events.update(event_pairs)
                while self._events:
                    fd, events = self._events.popitem()
                    try:
                        self._handlers[fd](fd, events)
                    except Exception as e:
                        print('handlers exception...', e)
                        raise
        finally:
            IOLoop._current.instance = old_current
            print('end of the world')


if __name__ == '__main__':
    p = IOLoop()
    print(hasattr(p, 'instance'))
    q = IOLoop.instance()
    print(hasattr(q, 'instance'))

    print(hasattr(IOLoop._current, 'instance'))

# SPASM: Spasm Passes as a State Machine
# https://gist.github.com/andyortlieb/0e28e0d02c2b27c60c5f
# Author: Andy Ortlieb <YW5keW9ydGxpZWJAZ21haWwuY29t>

import datetime
import logging
LOGGER = logging.getLogger("spasm")


# Some provided callbacks

class TransitionException(Exception):
    pass


class InvalidTransition(TransitionException):
    pass


class ErroneousTransition(TransitionException):
    pass


class DeniedTransition(TransitionException):
    pass


class Stop(Exception):
    # Used for flow control, raises after a successful transition.
    pass


def IgnoreTransition(*args, **kwargs):
    return False


def AllowTransition(*args, **kwargs):
    return True


# Workhorse

class State(object):
    pass


class _Initializing(State):
    pass

initializing = _Initializing()


class Unset(State):
    pass


class LoggedTransition(object):
    def __init__(self, sm, fro, to):
        self.sm = sm
        self.fro = fro
        self.to = to
        self.success = False
        self.timestamp = datetime.datetime.now()

    def __repr__(self):
        return "[%s success=%s] %s -> %s" % (
            self.timestamp, self.success,
            self.fro, self.to
        )


class StateMachine(object):
    _current = Unset()
    allow_log = None

    void_cb = IgnoreTransition
    allow_cb = AllowTransition
    ignore_cb = IgnoreTransition
    deny_cb = DeniedTransition

    initial_state = initializing

    def setup(self):
        pass

    def __init__(self, initial_state=None,
                 void_cb=None, allow_cb=None, ignore_cb=None, deny_cb=None,
                 allow_log=None):

        self._transition_log = []
        self._rules = {}
        self._steps = {}

        self.initial_state = initial_state or self.initial_state
        self.void_cb = void_cb or self.void_cb
        self.allow_cb = allow_cb or self.allow_cb
        self.ignore_cb = ignore_cb or self.ignore_cb
        self.deny_cb = deny_cb or self.deny_cb
        self.allow_log = allow_log if (allow_log is not None) else self.allow_log

        self.setup()
        self._current = self.initial_state

    # Add an automatic step
    def step(self, fro, to, callback=None):
        if fro in self._steps:
            LOGGER.warn(
                "StateMachine.step() will replace %s->%s with %s-%s",
                fro, self._steps[fro], fro, to)

        self._steps[fro] = to

        if callback:
            if (fro, to) in self._rules:
                LOGGER.warn(
                    "StateMachine.step() will override an existing rule for %s->%s",
                    fro, to)
            self.rule(fro, to, callback)
        else:
            if (fro, to) not in self._rules:
                LOGGER.info(
                    "StateMachine.step() will automatically add an allow rule for %s->%s",
                    fro, to)
                self.allow(fro, to)

    # Add or update a transition rule
    def rule(self, fro, to, callback, step=False):
        self._rules[(fro, to)] = callback
        if step:
            self.step(fro, to)

    # Remove a rule
    def deleteRule(self, fro, to):
        del self._rules[(fro, to)]

    # allow,ignore,deny are shortcuts
    def allow(self, fro, to, callback=None, step=False):
        callback = callback or self.allow_cb
        self.rule(fro, to, callback, step)

    def ignore(self, fro, to, callback=None, step=False):
        callback = callback or self.ignore_cb
        self.rule(fro, to, callback, step)

    def deny(self, fro, to, callback=None, step=False):
        callback = callback or self.deny_cb
        self.rule(fro, to, callback, step)

    def set(self, to):
        fro = self.get()

        cb = self._rules.get(
            (fro, to),
            self.void_cb
        )

        if self.allow_log:
            logged = LoggedTransition(self, fro, to)
            self._transition_log.append(logged)

        if isinstance(cb, type) and issubclass(cb, TransitionException):
            raise cb("%s -> %s" % (fro, to))
        elif isinstance(cb, type) and issubclass(cb, Stop):
            result = cb
        else:
            result = cb(self, fro, to)

        if isinstance(result, type) and issubclass(result, TransitionException):
            raise result("%s -> %s" % (fro, to))

        if result is not False:
            self._current = to

        if result is not False and self.allow_log:
            logged.success = True

        if isinstance(result, type) and issubclass(result, Stop):
            raise result("%s -> %s" % (fro, to))

        return result

    def get(self):
        return self._current

    def next(self):
        if self.get() in self._steps:
            self.set(self._steps[self.get()])
        return self.get()

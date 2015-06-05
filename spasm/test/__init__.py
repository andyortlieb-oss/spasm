import logging

from spasm import (
    StateMachine, InvalidTransition, ErroneousTransition,
    DeniedTransition, Stop, AllowTransition)


try:
    xrange = xrange
except NameError:
    xrange = range


def test():
    import sys
    testlog = logging.getLogger("spasm.test")

    root = logging.getLogger()
    if not root.handlers:
        root.setLevel(logging.DEBUG)
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        root.addHandler(ch)

    def StartingOverCB(*args, **kwargs):
        testlog.info("Round and round we go yeehaw!")

    def BadStateCB(sm, fro, to):
        testlog.info("Woah woah I can't move this way: %s -> %s" % (fro, to))
        return False

    def prepare_rules(sm):
        sm.allow("beginning", "middle")
        sm.allow("middle", "end")
        sm.allow("end", "beginning")

    def circular_flow(sm):
        sm.set("middle")
        sm.set("end")
        sm.set("beginning")

    sm1 = StateMachine(allow_log=True, initial_state='beginning')
    prepare_rules(sm1)
    circular_flow(sm1)

    sm2 = StateMachine(allow_log=True, initial_state='beginning', void_cb=BadStateCB)
    prepare_rules(sm2)
    circular_flow(sm2)
    assert sm2.set("middle") is not False
    assert sm2.set("beginning") is False
    assert sm2.set("end") is not False

    sm3 = StateMachine(allow_log=True, initial_state='beginning', void_cb=ErroneousTransition)
    prepare_rules(sm3)
    circular_flow(sm3)

    try:
        sm3.set("beginning")
    except ErroneousTransition:
        testlog.info("Appropriate exception was raised")
    else:
        raise AssertionError("beginning->beginning should have raised ErroneousTransition")

    # Test that delete rule works
    sm4 = StateMachine(allow_log=True, initial_state='beginning', void_cb=DeniedTransition)
    prepare_rules(sm4)
    circular_flow(sm4)
    circular_flow(sm4)
    sm4.deleteRule('end', 'beginning')
    try:
        circular_flow(sm4)
    except DeniedTransition:
        testlog.info("Good. DeniedTransition found when doing circular_flow the third time.")
    else:
        raise AssertionError("circular_flow should have raised DeniedTransition.")

    sm4.ignore("end", "beginning")
    assert sm4.set("beginning") is False
    sm4.allow("end", "beginning")
    assert sm4.set("beginning")
    circular_flow(sm4)

    class NeatoStateMachine(StateMachine):
        allow_log = True
        initial_state = 'beginning'

        count_allow = 0
        count_ignore = 0

        def my_ignore(self, sm, fro, to):
            testlog.info("---- Ignore that one! %s->%s --- " % (fro, to))
            return False

        def my_allow(self, sm, fro, to):
            testlog.info("   ACCEPTED! %s ->  %s" % (fro, to))

        def my_deny(self, sm, fro, to):
            testlog.info(" ____ DENIED ____ %s -> %s " % (fro, to))
            return ErroneousTransition  # TransitionExceptions get raised uniformly when returned

        def my_void(self, sm, fro, to):
            testlog.info(" ____ VOID ____ %s -> %s " % (fro, to))
            return InvalidTransition

        ignore_cb = my_ignore
        allow_cb = my_allow
        deny_cb = my_deny
        void_cb = my_void

        def setup(self):
            self.allow("beginning", "middle")  # ok.
            self.allow("middle", "end")  # ok.
            self.ignore("beginning", "end")  # Cannot skip.
            self.deny("end", "beginning")  # cannot loop.

    sm5 = NeatoStateMachine()
    # ignored: beginning->end
    assert sm5.set("end") is False
    # allowed: beginning->middle
    assert sm5.set("middle") is not False
    # void: middle->beginning
    try:
        sm5.set("beginning")
    except InvalidTransition:
        pass
    else:
        raise AssertionError("ErroneousTransition was expected")
    # allowed: middle->end
    assert sm5.set("end") is not False
    # denied: end->beginning. cannot loop.
    try:
        sm5.set("beginning")
    except ErroneousTransition:
        pass
    else:
        raise AssertionError("ErroneousTransition was expected")

    sm6 = NeatoStateMachine()
    # This one uses the Stop sentinel
    sm6.allow("middle", "end", Stop)
    sm6.set("middle")
    try:
        sm6.set("end")
    except Stop:
        assert sm6._transition_log[-1].success
    else:
        raise AssertionError("Stop sentinel expected")

    sm7 = StateMachine(allow_log=True, initial_state='beginning')
    sm7.deny('end', 'beginning')
    sm7.step('beginning', 'middle')
    sm7.step('middle', 'end')
    sm7.step('end', 'beginning')

    sm7.next()
    assert sm7.get() == 'middle'
    sm7.next()
    assert sm7.get() == 'end'
    try:
        sm7.next()
    except DeniedTransition:
        pass
    else:
        raise AssertionError("Expected next from end to beginning to fail")

    testlog.info("attempting to cycle")
    sm7.step("end", "beginning", AllowTransition)
    assert sm7.next() == 'beginning'

    # start really shaking things up
    sm7.ignore('beginning', 'middle')
    assert sm7.next() == 'beginning'
    sm7.step('beginning', 'middle', AllowTransition)
    assert sm7.next() == 'middle'

    for x in xrange(0, 4):
        sm7.next()

    sm7.step("end", "afterlife", lambda a, b, c: True)
    sm7.allow("afterlife", "reincarnation", step=True)
    sm7.step("reincarnation", "beginning")

    start = len(sm7._transition_log)
    for x in range(15):
        sm7.next()
    assert (len(sm7._transition_log)-start) == 15

###############################################################################
# Here's just a rundown of what we did during the test.
    allsm = [sm1, sm2, sm3, sm4, sm5, sm6, sm7]

    import pprint
    for sm in allsm:
        print()
        print("State Machine Transition Log: %s" % sm)
        pprint.pprint(sm._transition_log)

    return allsm

if __name__ == '__main__':
    test()

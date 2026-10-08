from django.test import SimpleTestCase

from participation import states as s

# (mode, current) -> {target: state}; everything not listed must be refused.
# "seat" stands for registered, or waitlisted when full.
EXPECTED = {
    (s.OPT_OUT, None): {s.CANCELLED: s.CANCELLED, s.REGISTERED: s.REGISTERED},
    (s.OPT_OUT, s.REGISTERED): {s.CANCELLED: s.CANCELLED, s.REGISTERED: s.REGISTERED},
    (s.OPT_OUT, s.CANCELLED): {s.CANCELLED: s.CANCELLED, s.REGISTERED: s.REGISTERED},
    (s.OPT_OUT, s.WAITLISTED): {s.CANCELLED: s.CANCELLED},
    (s.OPT_OUT, s.APPLIED): {s.CANCELLED: s.CANCELLED},
    (s.OPT_OUT, s.ASSIGNED): {s.CANCELLED: s.CANCELLED},
    (s.OPT_OUT, s.NOT_SELECTED): {s.CANCELLED: s.CANCELLED},
    (s.OPT_IN, None): {s.REGISTERED: "seat", s.CANCELLED: s.CANCELLED},
    (s.OPT_IN, s.REGISTERED): {s.REGISTERED: s.REGISTERED, s.CANCELLED: s.CANCELLED},
    (s.OPT_IN, s.WAITLISTED): {s.REGISTERED: s.WAITLISTED, s.CANCELLED: s.CANCELLED},
    (s.OPT_IN, s.CANCELLED): {s.REGISTERED: "seat", s.CANCELLED: s.CANCELLED},
    (s.OPT_IN, s.APPLIED): {s.CANCELLED: s.CANCELLED},
    (s.OPT_IN, s.ASSIGNED): {s.CANCELLED: s.CANCELLED},
    (s.OPT_IN, s.NOT_SELECTED): {s.CANCELLED: s.CANCELLED},
    (s.ASSIGNMENT, None): {s.APPLIED: s.APPLIED, s.CANCELLED: s.CANCELLED},
    (s.ASSIGNMENT, s.APPLIED): {s.APPLIED: s.APPLIED, s.WITHDRAWN: s.CANCELLED, s.CANCELLED: s.CANCELLED},
    (s.ASSIGNMENT, s.ASSIGNED): {s.CANCELLED: s.CANCELLED},
    (s.ASSIGNMENT, s.CANCELLED): {s.APPLIED: s.APPLIED, s.CANCELLED: s.CANCELLED},
    (s.ASSIGNMENT, s.REGISTERED): {s.CANCELLED: s.CANCELLED},
    (s.ASSIGNMENT, s.WAITLISTED): {},
    (s.ASSIGNMENT, s.NOT_SELECTED): {},
}


class StateMachineTableTests(SimpleTestCase):
    def test_every_combination(self):
        count = 0
        for mode in s.MODES:
            for current in (None, *s.STATES):
                for target in s.TARGETS:
                    for full in (False, True):
                        count += 1
                        with self.subTest(mode=mode, current=current, target=target, full=full):
                            outcome = s.next_state(mode, current, target, full=full)
                            allowed = EXPECTED[(mode, current)]
                            if target in allowed:
                                want = allowed[target]
                                if want == "seat":
                                    want = s.WAITLISTED if full else s.REGISTERED
                                self.assertTrue(outcome.ok)
                                self.assertEqual(outcome.state, want)
                                self.assertEqual(outcome.noop, want == current)
                            else:
                                code = s.MODE_FORBIDDEN if target not in s.MODE_TARGETS[mode] else s.INVALID_TRANSITION
                                self.assertEqual((outcome.ok, outcome.state, outcome.code), (False, None, code))
        self.assertEqual(count, 3 * 7 * 4 * 2)
        self.assertEqual(set(EXPECTED), {(m, c) for m in s.MODES for c in (None, *s.STATES)})

    def test_mode_forbidden_examples(self):
        self.assertEqual(s.next_state(s.OPT_OUT, None, s.APPLIED).code, s.MODE_FORBIDDEN)
        self.assertEqual(s.next_state(s.OPT_IN, None, s.WITHDRAWN).code, s.MODE_FORBIDDEN)
        self.assertEqual(s.next_state(s.ASSIGNMENT, None, s.REGISTERED).code, s.MODE_FORBIDDEN)

    def test_waitlisted_stays_waitlisted_when_asked_again(self):
        outcome = s.next_state(s.OPT_IN, s.WAITLISTED, s.REGISTERED, full=False)
        self.assertEqual((outcome.state, outcome.noop), (s.WAITLISTED, True))

    def test_garbage_input_is_refused_not_raised(self):
        self.assertEqual(s.next_state("x", None, s.REGISTERED).code, s.INVALID_TRANSITION)
        self.assertEqual(s.next_state(s.OPT_IN, "x", s.REGISTERED).code, s.INVALID_TRANSITION)
        self.assertEqual(s.next_state(s.OPT_IN, None, "x").code, s.INVALID_TRANSITION)

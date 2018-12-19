# '//...' path is relative to the CWD where lucicfg is run.

load('//chromium.star', 'chromium')


chromium.test_set("a")
chromium.test_set("b")

chromium.test("t2", belong_to="b")
chromium.test("t1", belong_to="a")


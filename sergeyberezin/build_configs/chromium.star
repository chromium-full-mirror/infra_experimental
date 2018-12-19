# Chromium config module. Defines some primitives for generating configs.

load('@stdlib//internal/graph.star', 'graph')


kinds = struct(
    GN = 'chromium.gn',
    TESTS = 'chromium.tests',
    BUILDER = 'chromium.builder',
    BUILDERS = 'chromium.builders',
)


keys = struct(
    gn = lambda: graph.key(kinds.GN, '...'),  # singleton
    tests = lambda: graph.key(kinds.TESTS, '...'), # singleton
    builders = lambda: graph.key(kinds.BUILDERS, '...'),  # singleton
)

_tests = graph.add_node(keys.tests())

def test_set(name):
  key = graph.key('test_set', name)
  graph.add_node(key, props = {
    'name': name,
  })
  graph.add_edge(keys.tests(), key)


def test(name, belong_to):
  graph.add_node(graph.key('test', name), props = {'name': name})
  graph.add_edge(graph.key('test_set', belong_to), graph.key('test', name))


def gen(cfg):
  per_set = {}
  for s in graph.children(keys.tests(), 'test_set'):
    tests = []
    for t in graph.children(s.key, 'test'):
      tests.append(t.props.name)
    per_set[s.props.name] = tests
  cfg.config_set['hello.cfg'] = to_json(per_set) + "\n"


core.generator(impl = gen)


chromium = struct(
  test_set = test_set,
  test = test,
)

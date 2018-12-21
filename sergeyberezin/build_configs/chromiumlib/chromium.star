# Chromium config module. Defines some primitives for generating configs.

load('@stdlib//internal/graph.star', 'graph')


kinds = struct(
    RAW_TARGET = 'chromium.raw_target', # raw target names from BUILD.gn
    COMPILE_TARGET = 'chromium.compile_target',
    TEST_TARGET = 'chromium.test_target',
    BUILDER = 'chromium.builder',
    BUILDER_GROUP = 'chromium.builder_group',
    BUILDER_GROUPS = 'chromium.builder_groups',
    OS = 'chromium.os',  # Swarming "os" dimensions
)


keys = struct(
    raw_target = lambda name: graph.key(kinds.RAW_TARGET, name),
    test_target = lambda name: graph.key(kinds.TEST_TARGET, name),
    compile_target = lambda name: graph.key(kinds.COMPILE_TARGET, name),
    builder = lambda name: graph.key(kinds.BUILDER, name),
    builder_group = lambda name: graph.key(kinds.BUILDER_GROUP, name),
    builder_groups = lambda: graph.key(kinds.BUILDER_GROUPS, '...'), # singleton
    os = lambda name: graph.key(kinds.OS, name),
)


_builder_groups = graph.add_node(keys.builder_groups())

# A virtual group of all builders, not part of _builder_groups
_all_builders_key = keys.builder_group('all builders')
_builders = graph.add_node(_all_builders_key)


def _props(props_dict):
  # Keep properties both as struct attributes and as the original dict.
  props = {'__dict__': props_dict}
  props.update(props_dict)
  return props


def builder_group(name, builders=[], bucket=None):
  key = keys.builder_group(name)
  props = _props({
    'name': name,
    'bucket': bucket,
    'builders': builders,
  })
  graph.add_node(key, props)
  graph.add_edge(keys.builder_groups(), key)
  for builder in builders:
    graph.add_edge(key, keys.builder(builder))
  return name


def builder(name, additional_compile_targets=[], test_targets=[],
            on_try_failure=[]):
  key = keys.builder(name)
  props = _props({
    'name': name,
    'on_try_failure': on_try_failure,
    'additional_compile_targets': additional_compile_targets,
    'test_targets': test_targets,
  })
  graph.add_node(key, props)
  graph.add_edge(_all_builders_key, key)
  for t in additional_compile_targets:
    graph.add_edge(key, keys.compile_target(t))
  for t in test_targets:
    graph.add_edge(key, keys.test_target(t))
  return name


def compile_target(target_name,
                   target_platform,
                   name=None,
                   gn_args=[],
                   host_platform=None):
  if name == None:
    parts = [target_name, target_platform, ','.join([
      '%s=%s' % (k, v) for k, v in gn_args.items()])]
    if host_platform:
      parts.append(host_platform)
    name = '+'.join(parts)
  key = keys.compile_target(name)
  if not host_platform:
    host_platform = target_platform
  props = _props({
    'name': name,
    'target_name': target_name,
    'target_platform': target_platform,
    'host_platform': host_platform,
    'gn_args': gn_args,
  })
  graph.add_node(key, props)
  graph.add_edge(key, keys.raw_target(target_name))
  return name


def test_target(compile_target,
                os_list,  # list of os dimensions
                name=None,
                local_shards=1,
                remote_shards=1,
                test_args={}):
  if name == None:
    parts = [compile_target] + os_list
    parts.append('local_shards=%d' % local_shards)
    parts.append('remote_shards=%d' % local_shards)
    for k, v in test_args.items():
      parts.append('%s=%s' % (k, v))
    name = '+'.join(parts)
  key = keys.test_target(name)
  props = _props({
    'name': name,
    'compile_target': compile_target,
    'os': os_list,
    'local_shards': local_shards,
    'remote_shards': remote_shards,
    'test_args': test_args,
  })
  graph.add_node(key, props)
  graph.add_edge(key, keys.compile_target(compile_target))
  for os in os_list:
    graph.add_edge(key, keys.os(os))
  return name


def target_name(name):
  graph.add_node(keys.raw_target(name))
  return name


def os(name):
  graph.add_node(keys.os(name))
  return name


def gen(cfg):
  builders = []
  builder_groups = []
  for b in graph.children(_all_builders_key, kinds.BUILDER):
    builders.append(b.props.__dict__)

  for g in graph.children(keys.builder_groups(), kinds.BUILDER_GROUP):
    builder_groups.append(g.props.__dict__)

  cfg.config_set['builders.cfg'] = to_json(builders) + "\n"
  cfg.config_set['builder_groups.cfg'] = to_json(builder_groups) + "\n"


core.generator(impl = gen)


chromium = struct(
  builder_group = builder_group,
  builder = builder,
  compile_target = compile_target,
  test_target = test_target,
  target_name = target_name,
  os = os,
)

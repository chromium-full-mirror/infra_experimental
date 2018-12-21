load('//chromiumlib/chromium.star', 'chromium')


_builders = []


def builder(name, target_platform, gn_args, targets, test_os_list,
            test_args={}, host_platform=None):
  if not host_platform:
    host_platform = target_platform

  test_targets = []
  for t in targets:
    # Auto-generate the name.
    compile_target = chromium.compile_target(
      target_name = t,
      target_platform = target_platform,
      gn_args = gn_args,
      host_platform = host_platform)
    test_targets.append(chromium.test_target(
      compile_target = compile_target,
      os_list = test_os_list,
      test_args = test_args,
    ))

  builder = chromium.builder(
    name = name,
    test_targets = test_targets,
    on_try_failure = ['try-without-patch'],
  )
  _builders.append(builder)
  return builder


cq_builders = [
    'linux_chromium_rel_ng',
    'mac_chromium_rel_ng',
    'win_chromium_rel_ng',
]


chromium.builder_group(
    name = 'cq',
    builders = cq_builders,
    bucket = 'try',
)


builder(
    name = 'linux_chromium_rel_ng',
    target_platform = 'linux',
    gn_args = {'symbol_level': 1, 'target': 'Release'},
    targets = ['all'],
    test_os_list = ['Ubuntu-16.04'],
)


builder(
    name = 'mac_chromium_rel_ng',
    target_platform = 'mac',
    gn_args = {'symbol_level': 1, 'target': 'Release'},
    targets = ['all'],
    test_os_list = ['Mac-10.13'],
)


builder(
    name = 'win_chromium_rel_ng',
    target_platform = 'win',
    gn_args = {'symbol_level': 1, 'target': 'Release'},
    targets = ['all'],
    test_os_list = ['Windows-10'],
)


builders = struct(
  builders = _builders
)

load('//chromiumlib/chromium.star', 'chromium')

_common_targets = [
    'net_unittests',
]


_android_targets = [
    'cronet_package',
    'cronet_perf_test_apk',
    'dump_syms',
    'microdump_stackwalk',
    'cast_junit_test_lists',
    'cast_shell_apk',
    'cronet_sample_test_apk',
    'cronet_smoketests_missing_native_library_instrumentation_apk',
    'cronet_smoketests_platform_only_instrumentation_apk',
    'cronet_test_instrumentation_apk',
    'cronet_tests_android',
    'cronet_unittests_android',
 ]


_all_targets = ['all'] + _common_targets + _android_targets


def _targets():
  for target in _all_targets:
    chromium.target_name(target)
  return _all_targets


targets = struct(
  targets = _targets()
)

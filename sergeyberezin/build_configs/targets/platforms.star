load('//chromiumlib/chromium.star', 'chromium')


_platforms = [
  'Mac-10.13',
  'Ubuntu-14.04',
  'Ubuntu-16.04',
  'Windows-10',
]


def _add_platforms():
  for p in _platforms:
    chromium.os(p)
  return _platforms


platforms = struct(
    platforms = _add_platforms()
)

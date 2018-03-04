import argparse
import os
import shutil

URLS_TO_REMAP = ['elements', 'bower_components', 'static']

def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('mode')
  parser.add_argument('--build_dir', default='build/es6-bundled')

  args = parser.parse_args()
  if args.mode == 'dev':
    if os.path.exists('app.yaml.dev'):
      shutil.move('app.yaml.dev', 'app.yaml')
  elif args.mode == 'build':
    assert os.path.exists(args.build_dir), '%s must exist' % args.build_dir
    build_dir = args.build_dir.strip('/')

    with open('app.yaml') as f:
      lines = f.readlines()

    new_lines = []
    i = 0
    while i < len(lines):
      l = lines[i]
      found = False
      for url in URLS_TO_REMAP:
        if l.startswith('- url: /' + url):
          found = True
          while i < len(lines):
            if lines[i].strip().startswith('static_dir:'):
              new_lines.append(lines[i].split(':')[0] + ': %s/%s' % (build_dir, url) + '\n')
              break
            else:
              new_lines.append(lines[i])
            i += 1
      if not found:
        new_lines.append(l)
      i += 1

    shutil.move('app.yaml', 'app.yaml.dev')
    with open('app.yaml', 'w') as f:
      f.writelines(new_lines)

if __name__ == '__main__':
  main()

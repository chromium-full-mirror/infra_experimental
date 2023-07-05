import logging
import os
import functools

from flask import Flask, g

import sidecar


# Groups checked for every request. Predeclaring them and passing to
# Authenticate cuts on number of RPCs. This list should only contain groups
# that will have to be checked on almost every request anyhow (usually groups
# use for broad access control, like admin checks).
GROUPS_TO_CHECK_ON_AUTHENTICATION = [
    'mdb/chrome-troopers',
]


def create_app():
  app = Flask(__name__)

  # Route logs appropriately when running under gunicorn.
  if __name__ != '__main__':
    gunicorn_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)

  # This also waits for the sidecar server to start and become healthy.
  sidecar.init(app, os.environ.get('LUCI_SIDECARE_ADDR', '127.0.0.1:8801'))

  return app


app = create_app()


@app.route('/healthz')
def healthz():
  return 'OK'


@app.route('/')
@sidecar.authenticate(GROUPS_TO_CHECK_ON_AUTHENTICATION)
def hello_world():
  return f'Hello {g.auth_ctx.identity}!\n'


@app.route('/group/<path:group>')
@sidecar.authenticate(GROUPS_TO_CHECK_ON_AUTHENTICATION)
def group(group):
  yes = g.auth_ctx.is_member(group)
  if yes:
    return f'Hello {g.auth_ctx.identity}! You are a member of {group}.\n'
  return f'Hello {g.auth_ctx.identity}! You are not a member of {group}.\n'


@app.route('/permission/<perm>/<path:realm>')
@sidecar.authenticate(GROUPS_TO_CHECK_ON_AUTHENTICATION)
def permission(perm, realm):
  yes = g.auth_ctx.has_permission(perm, realm)
  if yes:
    return f'Hello {g.auth_ctx.identity}! You have {perm} in {realm}.\n'
  return f'Hello {g.auth_ctx.identity}! You don\'t have {perm} in {realm}.\n'


if __name__ == '__main__':
  app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

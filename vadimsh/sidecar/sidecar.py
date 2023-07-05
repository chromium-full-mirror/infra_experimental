import functools
import threading
import time

import flask
import grpc

from grpc_health.v1 import health
from grpc_health.v1 import health_pb2
from grpc_health.v1 import health_pb2_grpc

from luci.common.proto.sidecar import auth_pb2
from luci.common.proto.sidecar import auth_pb2_grpc


class SidecarError(Exception):
  def __init__(self, message, http_code):
    super().__init__(message)
    self.http_code = http_code


class Sidecar:
  """Pure wrapper over LUCI Sidecar gRPC server."""

  def __init__(self, addr, logger):
    self._logger = logger
    self._channel = grpc.insecure_channel(addr)
    self._auth_stub = auth_pb2_grpc.AuthStub(self._channel)

  def wait_healthy(self):
    health_stub = health_pb2_grpc.HealthStub(self._channel)
    while True:
      try:
        res = health_stub.Check(health_pb2.HealthCheckRequest(), timeout=1.0)
        if res.status == health_pb2.HealthCheckResponse.SERVING:
          break
        self._logger.info('Waiting for LUCI sidecar: %s', res.status)
      except grpc.RpcError as exc:
        self._logger.info('Waiting for LUCI sidecar: %s', exc.code())
      time.sleep(0.5)
    self._logger.info('LUCI sidecar is ready')

  def authenticate_http(self, headers, groups=None):
    try:
      res = self._auth_stub.Authenticate(auth_pb2.AuthenticateRequest(
          protocol=auth_pb2.AuthenticateRequest.Protocol.HTTP1,
          metadata=[
              {'key': key, 'value': val}
              for key, val in headers.items()
          ],
          groups=groups,
      ), timeout=10.0)
      if res.HasField('error'):
        self._logger.error('Bad credentials: %s', res.error)
        raise SidecarError(str(res.error), 401)
      return res
    except grpc.RpcError as exc:
      self._logger.error('Authenticate unexpectedly failed: %s', exc)
      raise SidecarError('Internal authentication error', 500) from exc

  def is_member(self, identity, groups):
    try:
      res = self._auth_stub.IsMember(auth_pb2.IsMemberRequest(
          identity=identity,
          groups=groups,
      ), timeout=10.0)
      return res.is_member
    except grpc.RpcError as exc:
      self._logger.error('IsMember unexpectedly failed: %s', exc)
      raise SidecarError('Internal group check error', 500) from exc

  def has_permission(self, identity, permission, realm, attrs=None):
    try:
      res = self._auth_stub.HasPermission(auth_pb2.HasPermissionRequest(
          identity=identity,
          permission=permission,
          realm=realm,
          attributes=attrs,
      ), timeout=10.0)
      return res.has_permission
    except grpc.RpcError as exc:
      self._logger.error('HasPermission unexpectedly failed: %s', exc)
      raise SidecarError('Internal permission check error', 500) from exc


class Context:
  """Lives in Flask context as `auth_ctx` and stores authentication state."""

  def __init__(self, sidecar, auth_resp, checked_groups):
    self._sidecar = sidecar
    self._auth_resp = auth_resp
    self._groups_checked_on_auth = checked_groups

  @property
  def identity(self):
    """The authenticated caller identity (can be anonymous!)."""
    return self._auth_resp.identity

  @property
  def anonymous(self):
    """True if the request is anonymous."""
    return self._auth_resp.identity == 'anonymous:anonymous'

  def is_member(self, group):
    """True if the caller is a member of this group."""
    # Quick path for groups already checked during authentication.
    if group in self._groups_checked_on_auth:
      return group in self._auth_resp.groups
    # Slower dynamic check via an RPC to the sidecar.
    return self._sidecar.is_member(self.identity, [group])

  def has_permission(self, permission, realm, attrs=None):
    """True if the caller has the given permission in the given realm."""
    return self._sidecar.has_permission(self.identity, permission, realm)


def init(app, addr):
  """Initializes LUCI sidecar and puts it into Flash context as `g.sidecar`."""
  sidecar = Sidecar(addr, logger=app.logger)
  sidecar.wait_healthy()

  @app.before_request
  def inject_sidecar():
    flask.g.sidecar = sidecar


def authenticate(groups=None):
  """A decorator that performs authentication via the sidecar RPC.

  On success it populates `g.auth_ctx` with an instance of Context(...). Fails
  only if the request has credentials attached and they are invalid. If the
  request doesn't have credentials attached, authentication is successful,
  but `g.auth_ctx.anonymous` is True.

  Accepts a list of groups to "precache" membership checks in. It can be empty.
  The outcome of these checks should still be checked using is_member(...) as
  usual. This is an optimization to cut on number of RPCs. This list should only
  contain groups that will have to be checked on almost every request anyhow
  (usually used for broad access control, like admin checks).
  """
  groups = tuple(groups or [])
  def decorator(f):
    @functools.wraps(f)
    def decorated(*args, **kwargs):
      assert flask.g.get('sidecar') is not None
      assert flask.g.get('auth_ctx') is None
      try:
        resp = flask.g.sidecar.authenticate_http(
            headers=flask.request.headers,
            groups=groups,
        )
      except SidecarError as exc:
        return (str(exc), exc.http_code)
      flask.g.auth_ctx = Context(flask.g.sidecar, resp, groups)
      return f(*args, **kwargs)
    return decorated
  return decorator

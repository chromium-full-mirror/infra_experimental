from google.rpc import status_pb2 as _status_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class AuthenticateRequest(_message.Message):
    __slots__ = ["protocol", "metadata", "groups"]
    class Protocol(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
        PROTOCOL_UNSPECIFIED: _ClassVar[AuthenticateRequest.Protocol]
        HTTP1: _ClassVar[AuthenticateRequest.Protocol]
        HTTP2: _ClassVar[AuthenticateRequest.Protocol]
        GRPC: _ClassVar[AuthenticateRequest.Protocol]
    PROTOCOL_UNSPECIFIED: AuthenticateRequest.Protocol
    HTTP1: AuthenticateRequest.Protocol
    HTTP2: AuthenticateRequest.Protocol
    GRPC: AuthenticateRequest.Protocol
    class Metadata(_message.Message):
        __slots__ = ["key", "value"]
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    PROTOCOL_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    GROUPS_FIELD_NUMBER: _ClassVar[int]
    protocol: AuthenticateRequest.Protocol
    metadata: _containers.RepeatedCompositeFieldContainer[AuthenticateRequest.Metadata]
    groups: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, protocol: _Optional[_Union[AuthenticateRequest.Protocol, str]] = ..., metadata: _Optional[_Iterable[_Union[AuthenticateRequest.Metadata, _Mapping]]] = ..., groups: _Optional[_Iterable[str]] = ...) -> None: ...

class AuthenticateResponse(_message.Message):
    __slots__ = ["identity", "server_info", "groups", "error", "anonymous", "user", "project"]
    class Anonymous(_message.Message):
        __slots__ = []
        def __init__(self) -> None: ...
    class User(_message.Message):
        __slots__ = ["email", "name", "picture", "client_id"]
        EMAIL_FIELD_NUMBER: _ClassVar[int]
        NAME_FIELD_NUMBER: _ClassVar[int]
        PICTURE_FIELD_NUMBER: _ClassVar[int]
        CLIENT_ID_FIELD_NUMBER: _ClassVar[int]
        email: str
        name: str
        picture: str
        client_id: str
        def __init__(self, email: _Optional[str] = ..., name: _Optional[str] = ..., picture: _Optional[str] = ..., client_id: _Optional[str] = ...) -> None: ...
    class Project(_message.Message):
        __slots__ = ["project", "service"]
        PROJECT_FIELD_NUMBER: _ClassVar[int]
        SERVICE_FIELD_NUMBER: _ClassVar[int]
        project: str
        service: str
        def __init__(self, project: _Optional[str] = ..., service: _Optional[str] = ...) -> None: ...
    IDENTITY_FIELD_NUMBER: _ClassVar[int]
    SERVER_INFO_FIELD_NUMBER: _ClassVar[int]
    GROUPS_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    ANONYMOUS_FIELD_NUMBER: _ClassVar[int]
    USER_FIELD_NUMBER: _ClassVar[int]
    PROJECT_FIELD_NUMBER: _ClassVar[int]
    identity: str
    server_info: ServerInfo
    groups: _containers.RepeatedScalarFieldContainer[str]
    error: _status_pb2.Status
    anonymous: AuthenticateResponse.Anonymous
    user: AuthenticateResponse.User
    project: AuthenticateResponse.Project
    def __init__(self, identity: _Optional[str] = ..., server_info: _Optional[_Union[ServerInfo, _Mapping]] = ..., groups: _Optional[_Iterable[str]] = ..., error: _Optional[_Union[_status_pb2.Status, _Mapping]] = ..., anonymous: _Optional[_Union[AuthenticateResponse.Anonymous, _Mapping]] = ..., user: _Optional[_Union[AuthenticateResponse.User, _Mapping]] = ..., project: _Optional[_Union[AuthenticateResponse.Project, _Mapping]] = ...) -> None: ...

class IsMemberRequest(_message.Message):
    __slots__ = ["identity", "groups"]
    IDENTITY_FIELD_NUMBER: _ClassVar[int]
    GROUPS_FIELD_NUMBER: _ClassVar[int]
    identity: str
    groups: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, identity: _Optional[str] = ..., groups: _Optional[_Iterable[str]] = ...) -> None: ...

class IsMemberResponse(_message.Message):
    __slots__ = ["is_member", "server_info"]
    IS_MEMBER_FIELD_NUMBER: _ClassVar[int]
    SERVER_INFO_FIELD_NUMBER: _ClassVar[int]
    is_member: bool
    server_info: ServerInfo
    def __init__(self, is_member: bool = ..., server_info: _Optional[_Union[ServerInfo, _Mapping]] = ...) -> None: ...

class HasPermissionRequest(_message.Message):
    __slots__ = ["identity", "permission", "realm", "attributes"]
    class AttributesEntry(_message.Message):
        __slots__ = ["key", "value"]
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    IDENTITY_FIELD_NUMBER: _ClassVar[int]
    PERMISSION_FIELD_NUMBER: _ClassVar[int]
    REALM_FIELD_NUMBER: _ClassVar[int]
    ATTRIBUTES_FIELD_NUMBER: _ClassVar[int]
    identity: str
    permission: str
    realm: str
    attributes: _containers.ScalarMap[str, str]
    def __init__(self, identity: _Optional[str] = ..., permission: _Optional[str] = ..., realm: _Optional[str] = ..., attributes: _Optional[_Mapping[str, str]] = ...) -> None: ...

class HasPermissionResponse(_message.Message):
    __slots__ = ["has_permission", "server_info"]
    HAS_PERMISSION_FIELD_NUMBER: _ClassVar[int]
    SERVER_INFO_FIELD_NUMBER: _ClassVar[int]
    has_permission: bool
    server_info: ServerInfo
    def __init__(self, has_permission: bool = ..., server_info: _Optional[_Union[ServerInfo, _Mapping]] = ...) -> None: ...

class ServerInfo(_message.Message):
    __slots__ = ["sidecar_service", "sidecar_job", "sidecar_host", "sidecar_version", "auth_db_service", "auth_db_rev"]
    SIDECAR_SERVICE_FIELD_NUMBER: _ClassVar[int]
    SIDECAR_JOB_FIELD_NUMBER: _ClassVar[int]
    SIDECAR_HOST_FIELD_NUMBER: _ClassVar[int]
    SIDECAR_VERSION_FIELD_NUMBER: _ClassVar[int]
    AUTH_DB_SERVICE_FIELD_NUMBER: _ClassVar[int]
    AUTH_DB_REV_FIELD_NUMBER: _ClassVar[int]
    sidecar_service: str
    sidecar_job: str
    sidecar_host: str
    sidecar_version: str
    auth_db_service: str
    auth_db_rev: int
    def __init__(self, sidecar_service: _Optional[str] = ..., sidecar_job: _Optional[str] = ..., sidecar_host: _Optional[str] = ..., sidecar_version: _Optional[str] = ..., auth_db_service: _Optional[str] = ..., auth_db_rev: _Optional[int] = ...) -> None: ...

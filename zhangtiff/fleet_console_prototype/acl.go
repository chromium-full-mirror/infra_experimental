// Copyright 2024 The Chromium Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

package main

import (
	"go.chromium.org/luci/server/auth/rpcacl"
)

const (
	// This is a LUCI Auth group that gets access to this service.
	FleetConsoleGroup = "fleet-console-access"
)

var RPCAccessInterceptor = rpcacl.Interceptor(rpcacl.Map{
	"/fleet_console_prototype.apipb/*": FleetConsoleGroup,
})

// Copyright 2016 The Chromium Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

package com.googlesource.chromium.plugins.gitnumberer;

class GitNumberValidationError extends Exception {
  private static final long serialVersionUID = 1L;

  String error;

  public GitNumberValidationError(String error) {
    this.error = error;
  }

  @Override
  public String toString() {
    return this.getClass().getName() + "(" + this.error + ")";
  }
}

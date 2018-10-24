// Copyright 2016 The Chromium Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

package com.googlesource.chromium.plugins.gitnumberer;

import java.util.Objects;

class CommitPositionValue {
  public final String branch;
  public final int number;

  public CommitPositionValue(String branch, int number) {
    this.number = number;
    this.branch = branch;
  }

  @Override
  public int hashCode() {
    return Objects.hash(branch, number);
  }

  @Override
  public boolean equals(Object obj) {
    if (this == obj) return true;
    if (obj == null) return false;
    if (!(obj instanceof CommitPositionValue)) return false;
    CommitPositionValue other = (CommitPositionValue) obj;
    if (branch == null) {
      if (other.branch != null) return false;
    } else if (!branch.equals(other.branch)) return false;
    if (number != other.number) return false;
    return true;
  }

  @Override
  public String toString() {
    return "CommitPositionValue [branch=" + branch + ", number=" + number + "]";
  }
}

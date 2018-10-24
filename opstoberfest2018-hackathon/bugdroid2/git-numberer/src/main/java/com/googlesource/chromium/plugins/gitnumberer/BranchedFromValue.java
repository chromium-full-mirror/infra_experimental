// Copyright 2016 The Chromium Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

package com.googlesource.chromium.plugins.gitnumberer;

import java.util.Objects;

public class BranchedFromValue extends CommitPositionValue {
  public final String commitId;

  public BranchedFromValue(String commitId, String branch, int number) {
    super(branch, number);
    this.commitId = commitId;
  }

  @Override
  public int hashCode() {
    return Objects.hash(branch, number, commitId);
  }

  @Override
  public boolean equals(Object obj) {
    if (this == obj) return true;
    if (!super.equals(obj)) return false;
    if (!(obj instanceof BranchedFromValue)) return false;
    BranchedFromValue other = (BranchedFromValue) obj;
    if (commitId == null) {
      if (other.commitId != null) return false;
    } else if (!commitId.equals(other.commitId)) return false;
    return true;
  }

  @Override
  public String toString() {
    return "CommitPositionValue [branch="
        + branch
        + ", number="
        + number
        + ", commit="
        + commitId
        + "]";
  }
}

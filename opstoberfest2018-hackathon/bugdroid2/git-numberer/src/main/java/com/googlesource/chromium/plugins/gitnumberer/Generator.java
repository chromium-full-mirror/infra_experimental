// Copyright 2016 The Chromium Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

package com.googlesource.chromium.plugins.gitnumberer;

import static com.google.common.base.Preconditions.checkNotNull;

import com.google.gerrit.server.config.PluginConfig;
import org.eclipse.jgit.revwalk.RevCommit;

public class Generator {
  public static boolean isEnabled(String ref, PluginConfig pluginConfig) {
    return GitNumbererModule.isRefEnabled(
        ref,
        "generation",
        pluginConfig.getStringList(ConfigFields.GENERATE_ENABLED),
        pluginConfig.getStringList(ConfigFields.GENERATE_DISABLED));
  }

  /**
   * Generates message for child commit that is about to be landed to the destination ref given its
   * future parent.
   *
   * <p>Intended use is for Gerrit changes that are being submitted. Therefore, the destination ref
   * must be already existing and its tip must be known. While it is possible to review change for
   * the very first commit on a yet to be created first ever branch in a project in Gerrit, it's
   * practically never done, and so this code doesn't support such case.
   *
   * @param expectedParent tip of destination branch which is to become child's parent
   * @param childCommitMessage the proposed message for the child commit.
   * @param destRef destination ref
   * @return commit message with footers based on current childCommitMessage.
   */
  public static String childMessage(
      RevCommit expectedParent, String childCommitMessage, String destRef)
      throws GitNumberValidationError {
    checkNotNull(expectedParent);
    PositionFooters pfParent = PositionFooters.extract(expectedParent);
    if (!pfParent.errors.isEmpty())
      throw new GitNumberValidationError(pfParent.formatErrors(expectedParent));

    StringBuilder newMessage = MessageTweaker.copyAndModifyingFooters(childCommitMessage);
    // Post-condition: we are appending lines to last paragraph
    // and all prior footers like Change-Id are already in this paragraph.

    if (destRef.equals(pfParent.position.branch)) {
      PositionFooters.appendCommitPosition(newMessage, destRef, pfParent.position.number + 1);
    } else {
      PositionFooters.appendCommitPosition(newMessage, destRef, 1);
      PositionFooters.appendBranchedFrom(newMessage, expectedParent.getName(), pfParent.position);
    }
    PositionFooters.copyBranchedFrom(newMessage, pfParent);
    return newMessage.toString();
  }
}

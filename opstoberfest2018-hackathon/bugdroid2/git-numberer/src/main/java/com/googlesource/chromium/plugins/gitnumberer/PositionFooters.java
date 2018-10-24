// Copyright 2016 The Chromium Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

package com.googlesource.chromium.plugins.gitnumberer;

import static com.google.common.base.Preconditions.checkState;

import com.google.common.base.Joiner;
import com.google.common.collect.Lists;
import java.util.ArrayList;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import org.eclipse.jgit.lib.ObjectId;
import org.eclipse.jgit.revwalk.FooterLine;
import org.eclipse.jgit.revwalk.RevCommit;

/** Keeps parsed information of git number footers of a particular commit. */
class PositionFooters {

  // TODO(tandrii): make these configurable in plugin conf per repo.
  public static final String PREFIX = "Cr-";
  public static final String COMMIT_POSITION = PREFIX + "Commit-Position";
  public static final String BRANCHED_FROM = PREFIX + "Branched-From";
  public static final String ORIGINAL = "Original-";

  /** The first position on a branch. */
  public static final int INITIAL_POSITION = 1;

  public final CommitPositionValue position;
  /** Lineage information, from bottom to top of commit message. */
  public final List<BranchedFromValue> branchedFrom;

  public final List<String> errors;

  /** Nicely formats 1 or more errors. */
  public String formatErrors(ObjectId forParent) {
    StringBuilder builder = new StringBuilder();
    checkState(!errors.isEmpty());
    if (errors.size() == 1) builder.append(errors.get(0));
    else builder.append("[").append(Joiner.on(", ").join(errors)).append("]");
    if (forParent != null) builder.append(" in parent commit ").append(forParent.getName());
    return builder.toString();
  }

  /** Extracts Git number footers from a commit. */
  public static PositionFooters extract(RevCommit commit) {
    CommitPositionValue position = null;
    boolean seen_position = false;
    List<BranchedFromValue> branchedFrom = new ArrayList<>();
    List<String> errors = new ArrayList<>();
    for (FooterLine line : Lists.reverse(commit.getFooterLines())) {
      if (line.getKey().equals(COMMIT_POSITION)) {
        if (seen_position) {
          errors.add("Only one " + COMMIT_POSITION + " footer value allowed");
          position = null;
          continue;
        }
        seen_position = true;
        Matcher m = RE_COMMIT_POSITION.matcher(line.getValue());
        if (!m.matches()) {
          errors.add("Invalid " + COMMIT_POSITION + " footer value");
          continue;
        }
        position = new CommitPositionValue(m.group(1), Integer.parseInt(m.group(2)));
      } else if (line.getKey().equals(BRANCHED_FROM)) {
        if (seen_position) {
          errors.add(BRANCHED_FROM + " footer not allowed before " + COMMIT_POSITION);
          break;
        }
        Matcher m = RE_BRANCHED_FROM.matcher(line.getValue());
        if (!m.matches()) {
          errors.add("Invalid " + BRANCHED_FROM + " footer value");
          continue;
        }
        branchedFrom.add(
            new BranchedFromValue(m.group(1), m.group(2), Integer.parseInt(m.group(3))));
      }
    }
    if (!seen_position) {
      errors.add(PositionFooters.COMMIT_POSITION + " footer is required");
    }
    return new PositionFooters(position, branchedFrom, errors);
  }

  protected PositionFooters(
      CommitPositionValue position, List<BranchedFromValue> branchedFrom, List<String> errors) {
    this.position = position;
    this.branchedFrom = branchedFrom;
    this.errors = errors;
  }

  /** Adds COMMIT_POSITION footer. */
  public static void appendCommitPosition(StringBuilder newMessage, String ref, int number) {
    newMessage
        .append('\n')
        .append(COMMIT_POSITION)
        .append(": ")
        // For example, refs/heads/master@{#287136}
        .append(ref)
        .append("@{#")
        .append(number)
        .append("}");
  }

  /** Adds BRANCHED_FROM footer given parent's hash and position. */
  public static void appendBranchedFrom(
      StringBuilder newMessage, String parentId, CommitPositionValue parentPosition) {
    newMessage
        .append('\n')
        .append(BRANCHED_FROM)
        .append(": ")
        // For example, sha1-refs/heads/master@{#287136}
        .append(parentId)
        .append('-')
        .append(parentPosition.branch)
        .append("@{#")
        .append(parentPosition.number)
        .append("}");
  }

  /** Copy BRANCHED_FROM footers of the parent. */
  public static void copyBranchedFrom(StringBuilder newMessage, PositionFooters parent) {
    // Parent footers are ordered bottom-up, but are appending lines top-down.
    for (BranchedFromValue bfv : Lists.reverse(parent.branchedFrom)) {
      appendBranchedFrom(newMessage, bfv.commitId, bfv);
    }
  }

  /** Extracts them from Cr-Commit-Position footer, that looks like refs/heads/master@{#287136} */
  static final Pattern RE_COMMIT_POSITION = Pattern.compile("^(.*)@\\{#(\\d+)\\}$");

  /**
   * Extracts them from Cr-Branched-From footer, that looks like
   * deadbeaf12345678-refs/heads/master@{#287136}
   */
  static final Pattern RE_BRANCHED_FROM = Pattern.compile("^(\\p{XDigit}{40})-(.*)@\\{#(\\d+)\\}$");
}

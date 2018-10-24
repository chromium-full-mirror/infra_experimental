// Copyright 2016 The Chromium Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

package com.googlesource.chromium.plugins.gitnumberer;

import static com.google.common.truth.Truth.assertThat;

import org.eclipse.jgit.revwalk.RevCommit;
import org.junit.Test;

public class ValidatorTest extends AbstractRevWalkTest {

  static final String HASH40 = "0123456789abcdef0123456789abcdef01234567";
  static final String OTHER_HASH40 = "a0123456789abcdef0123456789abcdef0123456";

  @Test
  public void sameRefValid() throws Exception {
    assertValid(
        "refs/heads/master",
        "Parent\n\nCr-Commit-Position: refs/heads/master@{#10}",
        "Child \n\nCr-Commit-Position: refs/heads/master@{#11}");
  }

  @Test
  public void sameRefInvalidFooters() throws Exception {
    assertInvalid(
        "refs/heads/master",
        "Bad parent\n\nCr-Commit-Position: garbage",
        "Child \n\nCr-Commit-Position: refs/heads/master@{#11}",
        "Invalid Cr-Commit-Position footer value in parent commit {}");
    assertInvalid(
        "refs/heads/master",
        "Parent\n\nCr-Commit-Position: refs/heads/master@{#10}",
        "Child \n\nCr-Commit-Position: invalid1}",
        "Invalid Cr-Commit-Position footer value");

    assertInvalid(
        "refs/heads/master",
        "Parent\n\nCr-Commit-Position-Missing: refs/heads/master@{#10}",
        "Child \n\nCr-Commit-Position: invalid1}",
        "Cr-Commit-Position footer is required in parent commit {}");
    assertInvalid(
        "refs/heads/master",
        "Parent\n\nCr-Commit-Position: refs/heads/master@{#10}",
        "Child \n\nCr-Commit-Position-Missing: invalid1}",
        "Cr-Commit-Position footer is required");
  }

  @Test
  public void sameRefWrongPosition() throws Exception {
    assertInvalid(
        "refs/heads/master",
        "Parent\n\nCr-Commit-Position: refs/heads/master@{#10}",
        "Child \n\nCr-Commit-Position: refs/heads/master@{#10}",
        "Cr-Commit-Position footer must have position number 11");
    assertInvalid(
        "refs/heads/master",
        "Parent\n\nCr-Commit-Position: refs/heads/master@{#10}",
        "Child \n\nCr-Commit-Position: refs/heads/master@{#12}",
        "Cr-Commit-Position footer must have position number 11");
    assertInvalid(
        "refs/heads/master",
        "Parent\n\nCr-Commit-Position: refs/heads/master@{#12}",
        "Child \n\nCr-Commit-Position: refs/heads/master@{#10}",
        "Cr-Commit-Position footer must have position number 13");
  }

  @Test
  public void sameRefWrongBranch() throws Exception {
    assertInvalid(
        "refs/heads/master",
        "Parent\n\nCr-Commit-Position: refs/heads/wrong@{#10}",
        "Child \n\nCr-Commit-Position: refs/heads/wrong@{#11}",
        "Cr-Commit-Position footer must be for refs/heads/master");
  }

  @Test
  public void newBranch() throws Exception {
    assertValid(
        "refs/heads/branch",
        "Parent\n\nCr-Commit-Position: refs/heads/master@{#10}",
        "Child \n\nCr-Commit-Position: refs/heads/branch@{#1}\n"
            + "Cr-Branched-From: {}-refs/heads/master@{#10}");
  }

  @Test
  public void newBranchWrongPosition() throws Exception {
    assertInvalid(
        "refs/heads/branch",
        "Parent\n\nCr-Commit-Position: refs/heads/master@{#10}",
        "Child \n\nCr-Commit-Position: refs/heads/master@{#1}\n"
            + "Cr-Branched-From: {}-refs/heads/master@{#10}",
        "Cr-Commit-Position footer must be for refs/heads/branch");
  }

  @Test
  public void newBranchInheritLineage() throws Exception {
    assertInvalid(
        "refs/heads/branch",
        "Parent\n\nCr-Commit-Position: refs/heads/master@{#10}\n"
            + "Cr-Branched-From: "
            + HASH40
            + "-refs/inhereted@{#2}",
        "Child \n\nCr-Commit-Position: refs/heads/branch@{#1}\n"
            // Missing inherited lineage.
            + "Cr-Branched-From: {}-refs/heads/master@{#10}",
        "invalid lineage footers Cr-Branched-From");

    assertInvalid(
        "refs/heads/branch",
        "Parent\n\nCr-Commit-Position: refs/heads/master@{#10}\n"
            + "Cr-Branched-From: "
            + HASH40
            + "-refs/inhereted@{#2}",
        "Child \n\nCr-Commit-Position: refs/heads/branch@{#1}\n"
            // Wrong branch in lineage.
            + "Cr-Branched-From: "
            + HASH40
            + "-wrong/lineage@{#2}\n"
            + "Cr-Branched-From: {}-refs/heads/master@{#10}",
        "invalid lineage footers Cr-Branched-From");

    assertInvalid(
        "refs/heads/branch",
        "Parent\n\nCr-Commit-Position: refs/heads/master@{#10}\n"
            + "Cr-Branched-From: "
            + HASH40
            + "-refs/inhereted@{#2}",
        "Child \n\nCr-Commit-Position: refs/heads/branch@{#1}\n"
            + "Cr-Branched-From: "
            + HASH40
            + "-refs/inhereted@{#2}\n"
            // Wrong position in lineage.
            + "Cr-Branched-From: {}-refs/heads/master@{#9999999}",
        "invalid lineage footers Cr-Branched-From");

    assertInvalid(
        "refs/heads/branch",
        "Parent\n\nCr-Commit-Position: refs/heads/master@{#10}\n"
            + "Cr-Branched-From: "
            + HASH40
            + "-refs/inhereted@{#2}",
        "Child \n\nCr-Commit-Position: refs/heads/branch@{#1}\n"
            // New lineage must come on top.
            + "Cr-Branched-From: "
            + HASH40
            + "-refs/inhereted@{#2}\n"
            + "Cr-Branched-From: {}-refs/heads/master@{#10}",
        "invalid lineage footers Cr-Branched-From");

    assertValid(
        "refs/heads/branch",
        "Parent\n\nCr-Commit-Position: refs/heads/master@{#10}\n"
            + "Cr-Branched-From: "
            + HASH40
            + "-refs/inhereted@{#2}",
        "Child \n\nCr-Commit-Position: refs/heads/branch@{#1}\n"
            + "Cr-Branched-From: {}-refs/heads/master@{#10}\n"
            + "Cr-Branched-From: "
            + HASH40
            + "-refs/inhereted@{#2}");

    assertInvalid(
        "refs/heads/branch",
        "Parent\n\nCr-Commit-Position: refs/heads/master@{#10}\n"
            // The order of these two ...
            + "Cr-Branched-From: "
            + HASH40
            + "-refs/inhereted@{#2}\n"
            + "Cr-Branched-From: "
            + HASH40
            + "-refs/more@{#4}",
        "Child \n\nCr-Commit-Position: refs/heads/branch@{#1}\n"
            + "Cr-Branched-From: {}-refs/heads/master@{#10}\n"
            // ... should be preserved.
            + "Cr-Branched-From: "
            + HASH40
            + "-refs/more@{#4}\n"
            + "Cr-Branched-From: "
            + HASH40
            + "-refs/inhereted@{#2}",
        "invalid lineage footers Cr-Branched-From");
  }

  @Test
  public void duplicatedLineageIsError() throws Exception {
    assertInvalid(
        "refs/heads/branch",
        "Parent\n\nCr-Commit-Position: refs/heads/master@{#10}\n"
            + "Cr-Branched-From: "
            + HASH40
            + "-refs/dup@{#2}\n"
            + "Cr-Branched-From: "
            + HASH40
            + "-refs/dup@{#2}",
        "Child \n\nCr-Commit-Position: refs/heads/branch@{#1}\n"
            + "Cr-Branched-From: {}-refs/dup/dup@{#2}",
        "invalid lineage footers Cr-Branched-From");

    // Even if the same in parent && child.
    assertInvalid(
        "refs/heads/branch",
        "Parent\n\nCr-Commit-Position: refs/heads/master@{#10}\n"
            + "Cr-Branched-From: "
            + HASH40
            + "-refs/dup@{#2}\n"
            + "Cr-Branched-From: "
            + HASH40
            + "-refs/dup@{#2}",
        "Child \n\nCr-Commit-Position: refs/heads/branch@{#1}\n"
            + "Cr-Branched-From: "
            + HASH40
            + "-refs/dup@{#2}\n"
            + "Cr-Branched-From: "
            + HASH40
            + "-refs/dup@{#2}",
        "invalid lineage footers Cr-Branched-From");
  }

  @Test
  public void orphan() throws Exception {
    assertInvalid(
        "refs/heads/orphan",
        null,
        "Child \n\nCr-Commit-Position: refs/heads/orphan@{#1}\n"
            + "Cr-Branched-From: "
            + HASH40
            + "-refs/heads/master@{#10}",
        "Cr-Branched-From not allowed in the first commit of orphan branch");

    assertValid("refs/heads/orphan", null, "Child \n\nCr-Commit-Position: refs/heads/orphan@{#1}");
  }

  @Test
  public void immuneToCherryPicks() throws Exception {
    // It's generator's duty to generate this correctly, but it's not essential
    // from validator's perspective.
    assertValid(
        "refs/heads/branch",
        "Parent which branched from master\n\n"
            + "Cr-Commit-Position: refs/heads/branch@{#1}\n"
            + "Cr-Branched-From: "
            + HASH40
            + "-refs/heads/master@{#444}",
        "Child which is cherry-pick of 999 on master branch\n\n"
            + "Cr-Commit-Position: refs/heads/master@{#999}\n"
            + "(cherry picked from commit "
            + OTHER_HASH40
            + ")\n\n"
            + "Cr-Commit-Position: refs/heads/branch@{#2}\n"
            + "Cr-Branched-From: "
            + HASH40
            + "-refs/heads/master@{#444}");
  }

  void assertValid(String destBranch, String parentMessage, String commitMessage) throws Exception {
    RevCommit commit = mkCommits(parentMessage, commitMessage);
    try {
      CommitValidator.validate(getRevWalk(), commit, destBranch);
    } catch (GitNumberValidationError e) {
      assertThat(e.error).isEqualTo(""); // Better failure message.
      assertThat(e).isNull(); // To make sure test really does fail.
    }
  }

  void assertInvalid(String destBranch, String parentMessage, String commitMessage, String error)
      throws Exception {
    RevCommit commit = mkCommits(parentMessage, commitMessage);
    if (error.contains("{}")) error = error.replace("{}", commit.getParent(0).getName());
    try {
      CommitValidator.validate(getRevWalk(), commit, destBranch);
      assertThat("unreachable").isNull();
    } catch (GitNumberValidationError e) {
      assertThat(e.error).isEqualTo(error);
    }
  }
}

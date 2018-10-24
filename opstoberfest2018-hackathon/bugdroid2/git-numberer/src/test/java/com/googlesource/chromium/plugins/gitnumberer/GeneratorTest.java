// Copyright 2016 The Chromium Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

package com.googlesource.chromium.plugins.gitnumberer;

import static com.google.common.base.Preconditions.checkNotNull;
import static com.google.common.truth.Truth.assertThat;

import com.google.common.base.Joiner;
import org.eclipse.jgit.revwalk.RevCommit;
import org.junit.Test;

public class GeneratorTest extends AbstractRevWalkTest {
  static final String HASH40_1 = "1234567800000000123456780000000012345678";
  static final String HASH40_2 = "0000000012345678000000001234567800000000";
  static final String HASH40_3 = "abcdef0000000012345678000000001234567800";

  @Test
  public void sameBranchUseParentAsPassed() throws Exception {
    // https://chromium.googlesource.com/infra/infra/+/95626acc/infra/services/gnumbd/test/gnumbd_test.expected/branch.yaml
    new TestBuilder()
        .Parent("Parent", "", "Cr-Commit-Position: refs/heads/master@{#3}")
        .Child("Child")
        .DestinationBranch("refs/heads/master")
        .assertExpected("Child", "", "Cr-Commit-Position: refs/heads/master@{#4}");
  }

  @Test
  public void newBranch() throws Exception {
    // https://chromium.googlesource.com/infra/infra/+/95626acc/infra/services/gnumbd/test/gnumbd_test.expected/branch.yaml
    new TestBuilder()
        .Parent("Parent", "", "Cr-Commit-Position: refs/heads/master@{#3}")
        .Child("Child")
        .DestinationBranch("refs/heads/branch")
        .assertExpected(
            "Child",
            "",
            "Cr-Commit-Position: refs/heads/branch@{#1}",
            "Cr-Branched-From: {}-refs/heads/master@{#3}");
  }

  @Test
  public void newBranchWithLineage() throws Exception {
    // https://chromium.googlesource.com/infra/infra/+/95626acc/infra/services/gnumbd/test/gnumbd_test.expected/branch_from_branch.yaml
    new TestBuilder()
        .Parent(
            "Parent",
            "",
            "Cr-Commit-Position: refs/heads/branch@{#3}",
            "Cr-Branched-From: " + HASH40_1 + "-refs/heads/master@{#5}")
        .Child("Child")
        .DestinationBranch("refs/heads/more-branch")
        .assertExpected(
            "Child",
            "",
            "Cr-Commit-Position: refs/heads/more-branch@{#1}",
            "Cr-Branched-From: {}-refs/heads/branch@{#3}",
            "Cr-Branched-From: " + HASH40_1 + "-refs/heads/master@{#5}");
  }

  @Test
  public void sameBranchWithLineage() throws Exception {
    new TestBuilder()
        .Parent(
            "Parent",
            "",
            "Cr-Commit-Position: refs/heads/master@{#3}",
            "Cr-Branched-From: " + HASH40_1 + "-refs/heads/from@{#5}")
        .Child("Child")
        .DestinationBranch("refs/heads/master")
        .assertExpected(
            "Child",
            "",
            "Cr-Commit-Position: refs/heads/master@{#4}",
            "Cr-Branched-From: " + HASH40_1 + "-refs/heads/from@{#5}");
  }

  @Test
  public void doubleBranchingLineage() throws Exception {
    // Regression test for bug http://crbug.com/698845 .
    new TestBuilder()
        .Parent(
            "Version 5.8.283.6",
            "",
            "Cr-Commit-Position: refs/branch-heads/5.8@{#14}",
            "Cr-Branched-From: " + HASH40_1 + "-refs/heads/5.8.283@{#1}",
            "Cr-Branched-From: " + HASH40_2 + "-refs/heads/master@{#43429}")
        .Child("Child")
        .DestinationBranch("refs/branch-heads/5.8")
        .assertExpected(
            "Child",
            "",
            "Cr-Commit-Position: refs/branch-heads/5.8@{#15}",
            "Cr-Branched-From: " + HASH40_1 + "-refs/heads/5.8.283@{#1}",
            "Cr-Branched-From: " + HASH40_2 + "-refs/heads/master@{#43429}");
  }

  @Test
  public void sameBranchCherryPick() throws Exception {
    // https://chromium.googlesource.com/infra/infra/+/95626acc/infra/services/gnumbd/test/gnumbd_test.expected/cherry_pick_regression.yaml
    // Note the above test before assumes "Original-" is modified after move
    // of the footer from the original commit message. While here modification
    // is applied to a copy.
    new TestBuilder()
        .Parent(
            "Parent",
            "",
            "Cr-Commit-Position: refs/heads/branch@{#3}",
            "Cr-Branched-From: " + HASH40_1 + "-refs/heads/master@{#5}")
        .Child(
            "Cherry pick",
            "",
            "Cr-Commit-Position: refs/heads/master@{#88}",
            "Change-Id: Ideadbeef",
            "(cherry picked from commit " + HASH40_2 + ")")
        .DestinationBranch("refs/heads/branch")
        .assertExpected(
            "Cherry pick",
            "",
            "(cherry picked from commit " + HASH40_2 + ")",
            "",
            "Cr-Original-Commit-Position: refs/heads/master@{#88}",
            "Change-Id: Ideadbeef",
            "Cr-Commit-Position: refs/heads/branch@{#4}",
            "Cr-Branched-From: " + HASH40_1 + "-refs/heads/master@{#5}");
  }

  @Test
  public void doubleCherryPick() throws Exception {
    // https://chromium.googlesource.com/infra/infra/+/95626acc/infra/services/gnumbd/test/gnumbd_test.expected/cherry_pick_x_regression.yaml
    new TestBuilder()
        .Parent(
            "Parent",
            "",
            "Cr-Commit-Position: refs/heads/fork@{#3}",
            "Cr-Branched-From: " + HASH40_1 + "-refs/heads/master@{#66}")
        .Child(
            "Cherry pick of cherry pick",
            "",
            "(cherry picked from commit " + HASH40_2 + ")",
            "",
            "Cr-Original-Commit-Position: refs/heads/master@{#88}",
            "Cr-Commit-Position: refs/heads/branch@{#4}",
            "Cr-Branched-From: " + HASH40_2 + "-refs/heads/master@{#5}",
            "(cherry picked from commit " + HASH40_3 + ")")
        .DestinationBranch("refs/heads/fork")
        .assertExpected(
            "Cherry pick of cherry pick",
            "",
            "(cherry picked from commit " + HASH40_2 + ")",
            "",
            "(cherry picked from commit " + HASH40_3 + ")",
            "",
            "Cr-Original-Original-Commit-Position: refs/heads/master@{#88}",
            "Cr-Original-Commit-Position: refs/heads/branch@{#4}",
            "Cr-Original-Branched-From: " + HASH40_2 + "-refs/heads/master@{#5}",
            "Cr-Commit-Position: refs/heads/fork@{#4}",
            "Cr-Branched-From: " + HASH40_1 + "-refs/heads/master@{#66}");
  }

  @Test
  public void extraUserFooter() throws Exception {
    // https://chromium.googlesource.com/infra/infra/+/95626acc/infra/services/gnumbd/test/gnumbd_test.expected/extra_user_footer.yaml
    new TestBuilder()
        .Parent("Parent", "", "Cr-Commit-Position: refs/heads/master@{#3}")
        .Child(
            "Child",
            "",
            "Change-Id: Icafebabe1cec6eadfeba",
            "Reviewed-by: Cool Dudette 64 <cd64@example.com>",
            "Reviewed-by: Epic Sky Troll <est@example.com>",
            "Tested-by: Lol JK <lol_jk@example.com>")
        .DestinationBranch("refs/heads/master")
        .assertExpected(
            "Child",
            "",
            "Change-Id: Icafebabe1cec6eadfeba",
            "Reviewed-by: Cool Dudette 64 <cd64@example.com>",
            "Reviewed-by: Epic Sky Troll <est@example.com>",
            "Tested-by: Lol JK <lol_jk@example.com>",
            "Cr-Commit-Position: refs/heads/master@{#4}");
  }

  @Test
  public void extraUserFooterBad() throws Exception {
    // https://chromium.googlesource.com/infra/infra/+/95626acc/infra/services/gnumbd/test/gnumbd_test.expected/extra_user_footer_bad.yaml
    new TestBuilder()
        .Parent("Parent", "", "Cr-Commit-Position: refs/heads/master@{#3}")
        .Child("Child", "", "Cr-Double-Secret: I can impersonate the daemon!")
        .DestinationBranch("refs/heads/master")
        .assertExpected(
            "Child",
            "",
            "Cr-Original-Double-Secret: I can impersonate the daemon!",
            "Cr-Commit-Position: refs/heads/master@{#4}");
  }

  @Test
  public void footersWithPrefix() throws Exception {
    new TestBuilder()
        .Parent("Parent", "", "Cr-Commit-Position: refs/heads/master@{#3}")
        .Child("Child", "", "Cr-I-Am-Loving-It: the prefix")
        .DestinationBranch("refs/heads/master")
        .assertExpected(
            "Child",
            "",
            "Cr-Original-I-Am-Loving-It: the prefix",
            "Cr-Commit-Position: refs/heads/master@{#4}");
  }

  @Test
  public void someFootersAlreadyCorrect() throws Exception {
    new TestBuilder()
        .Parent(
            "Parent",
            "",
            "Cr-Commit-Position: refs/heads/master@{#3}",
            "Cr-Branched-From: " + HASH40_1 + "-refs/heads/base@{#5}")
        .Child(
            "Child which is way too smart", // aka - don't do it.
            "",
            "Change-Id: I0123deadbeef",
            "Cr-Commit-Position: refs/heads/master@{#4}")
        .DestinationBranch("refs/heads/master")
        .assertExpected(
            "Child which is way too smart",
            "",
            "Change-Id: I0123deadbeef",
            "Cr-Original-Commit-Position: refs/heads/master@{#4}",
            "Cr-Commit-Position: refs/heads/master@{#4}",
            "Cr-Branched-From: " + HASH40_1 + "-refs/heads/base@{#5}");
  }

  class TestBuilder {
    RevCommit parent = null;
    String childMessage = null;
    String destinationBranch = null;

    public TestBuilder Parent(String... lines) throws Exception {
      parent = writeCommit(null, Joiner.on("\n").join(lines));
      return this;
    }

    public TestBuilder Child(String... lines) throws Exception {
      checkNotNull(parent);
      childMessage = Joiner.on("\n").join(lines);
      return this;
    }

    public TestBuilder DestinationBranch(String destinationBranch) {
      this.destinationBranch = destinationBranch;
      return this;
    }

    public void assertExpected(String... lines) throws Exception {
      assertExpected(Joiner.on("\n").join(lines).replace("{}", parent.getName()), null);
    }

    public void assertInvalid(String exceptionMessage) throws Exception {
      assertExpected(null, exceptionMessage);
    }

    public void assertExpected(String newChildMessage, String exceptionMessage) throws Exception {
      checkNotNull(parent);
      checkNotNull(childMessage);
      checkNotNull(destinationBranch);
      getRevWalk().parseBody(parent);
      String actual;
      try {
        actual = Generator.childMessage(parent, childMessage, destinationBranch);
      } catch (GitNumberValidationError e) {
        assertThat(childMessage).named("exception '%s' not expected", e.error).isNull();
        assertThat(e.error).isEqualTo(exceptionMessage);
        return;
      }

      assertThat(exceptionMessage).isNull();
      assertThat(actual).isEqualTo(newChildMessage);
      // Bonus check: make sure Validator agrees.
      CommitValidator.validate(getRevWalk(), writeCommit(parent, actual), destinationBranch);
    }
  }

  @Test
  public void testBuilderMessages() throws Exception {
    TestBuilder t = new TestBuilder();
    t.Parent("a", "", "b").Child("d", "a").DestinationBranch("refs/heads/test");
    assertThat(t.parent.getFullMessage()).isEqualTo("a\n\nb");
    assertThat(t.childMessage).isEqualTo("d\na");
    assertThat(t.destinationBranch).isEqualTo("refs/heads/test");
  }
}

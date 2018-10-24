// Copyright 2016 The Chromium Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

package com.googlesource.chromium.plugins.gitnumberer;

import static com.google.common.truth.Truth.assertThat;

import org.eclipse.jgit.lib.ObjectId;
import org.eclipse.jgit.revwalk.RevCommit;
import org.junit.Test;

public class PositionFootersTest extends AbstractRevWalkTest {

  final String HASH = "89abcdef0123456789abcdef0123456789abcdef";

  @Test
  public void extractEmpty() throws Exception {
    PositionFooters p = extract("no footers");
    assertThat(p.branchedFrom).isEmpty();
    assertThat(p.errors).containsExactly("Cr-Commit-Position footer is required");
  }

  @Test
  public void extractOnlyOnePositionAllowed() throws Exception {
    PositionFooters p =
        extract(
            "Commit with two footers\n\n"
                + "Cr-Commit-Position: refs/heads/master@{#55}\n"
                + "Cr-Commit-Position: refs/heads/master@{#11}");
    assertThat(p.errors).hasSize(1);
    assertThat(p.errors).contains("Only one Cr-Commit-Position footer value allowed");
    assertThat(p.formatErrors(null)).isEqualTo("Only one Cr-Commit-Position footer value allowed");
  }

  @Test
  public void extractLineageBeforePositionNotAllowed() throws Exception {
    PositionFooters p =
        extract(
            "Commit with incorrect order of footers\n\n"
                + "Cr-Branched-From: 89abcdef0123456789abcdef0123456789abcdef-refs/heads/master@{#11}\n"
                + "Cr-Commit-Position: refs/heads/master@{#11}");
    assertThat(p.errors).hasSize(1);
    assertThat(p.errors).contains("Cr-Branched-From footer not allowed before Cr-Commit-Position");
  }

  @Test
  public void extractWithLineage() throws Exception {
    PositionFooters p =
        extract(
            "Commit with two lineage footers.\n\n"
                + "Cr-Commit-Position: refs/heads/release@{#10}\n"
                + "Cr-Branched-From: 89abcdef0123456789abcdef0123456789abcdef-refs/heads/master@{#11}\n"
                + "Cr-Branched-From: 0123456789abcdef0123456789abcdef01234567-refs/heads/beta-23@{#5}");
    assertThat(p.errors).isEmpty();
    assertThat(p.position).isNotNull();
    assertThat(p.position.branch).isEqualTo("refs/heads/release");
    assertThat(p.position.number).isEqualTo(10);

    assertThat(p.branchedFrom).hasSize(2);
    // Note that order is bottom-up.
    assertThat(p.branchedFrom.get(0).commitId)
        .isEqualTo("0123456789abcdef0123456789abcdef01234567");
    assertThat(p.branchedFrom.get(0).branch).isEqualTo("refs/heads/beta-23");
    assertThat(p.branchedFrom.get(0).number).isEqualTo(5);
    assertThat(p.branchedFrom.get(1).commitId)
        .isEqualTo("89abcdef0123456789abcdef0123456789abcdef");
    assertThat(p.branchedFrom.get(1).branch).isEqualTo("refs/heads/master");
    assertThat(p.branchedFrom.get(1).number).isEqualTo(11);
  }

  @Test
  public void extractLineageErrors() throws Exception {
    PositionFooters p =
        extract(
            "Commit with lineage errors\n\n"
                + "Cr-Commit-Position: not a footer because not in last paragraph\n\n"
                + "Cr-Commit-Position: refs/heads/release@{#10}\n"
                + "Cr-Branched-From: 0123456789abcdef0123456789abcdef01234567-ok@{#11}\n"
                + "Cr-Branched-From: bad-but-keep-parsing");
    assertThat(p.errors).hasSize(1);
    assertThat(p.errors).contains("Invalid Cr-Branched-From footer value");

    assertThat(p.position).isNotNull();
    assertThat(p.position.branch).isEqualTo("refs/heads/release");
    assertThat(p.position.number).isEqualTo(10);

    assertThat(p.branchedFrom).hasSize(1);
    assertThat(p.branchedFrom.get(0).commitId)
        .isEqualTo("0123456789abcdef0123456789abcdef01234567");
    assertThat(p.branchedFrom.get(0).branch).isEqualTo("ok");
    assertThat(p.branchedFrom.get(0).number).isEqualTo(11);
  }

  @Test
  public void extractLineageHashSize40Exact() throws Exception {
    String fortychars = "0123456789abcdef0123456789abcdef01234567";
    assertThat(fortychars).hasLength(40);
    PositionFooters p =
        extract(
            "Commit with off-by-one lineage error\n\n"
                + "Cr-Commit-Position: refs/heads/release@{#10}\n"
                + "Cr-Branched-From: "
                + fortychars.substring(1)
                + "not/ok@{#11}");
    assertThat(p.errors).hasSize(1);
    assertThat(p.errors).contains("Invalid Cr-Branched-From footer value");
  }

  @Test
  public void extractBranchPositionErrors() throws Exception {
    PositionFooters p =
        extract(
            "Commit with many errors\n\n"
                + "Cr-Commit-Position: malformed\n"
                + "Cr-Branched-From: 0123456789abcdef0123456789abcdef01234567-ok@{#11}");
    assertThat(p.errors).hasSize(1);
    assertThat(p.errors).contains("Invalid Cr-Commit-Position footer value");

    assertThat(p.position).isNull();

    assertThat(p.branchedFrom).hasSize(1);
    assertThat(p.branchedFrom.get(0).commitId)
        .isEqualTo("0123456789abcdef0123456789abcdef01234567");
    assertThat(p.branchedFrom.get(0).branch).isEqualTo("ok");
    assertThat(p.branchedFrom.get(0).number).isEqualTo(11);
  }

  @Test
  public void extractManyErrors() throws Exception {
    PositionFooters p =
        extract(
            "Commit with many errors\n\n" + "Cr-Commit-Position: bad\n" + "Cr-Branched-From: bad");
    assertThat(p.errors).hasSize(2);
    String expected =
        "[Invalid Cr-Branched-From footer value, " + "Invalid Cr-Commit-Position footer value]";
    assertThat(p.formatErrors(null)).isEqualTo(expected);
    assertThat(p.formatErrors(ObjectId.zeroId()))
        .isEqualTo(expected + " in parent commit " + ObjectId.zeroId().getName());
  }

  @Test
  public void regressionV8VersionBranch() throws Exception {
    PositionFooters p =
        extract(
            "Version 5.6.99\n\n"
                + "Performance and stability improvements on all platforms.\n\n"
                + "Cr-Commit-Position: refs/heads/5.6.99@{#1}\n"
                + "Cr-Branched-From: "
                + HASH
                + "-refs/heads/master@{#40407}");
    assertThat(p.errors).containsExactly();
    assertThat(p.position.branch).isEqualTo("refs/heads/5.6.99");
  }

  @Test
  public void noPositionDigits() throws Exception {
    PositionFooters p =
        extract(
            "A\n\n"
                + "Cr-Commit-Position: refs/head/master@{#}\n"
                + "Cr-Branched-From: "
                + HASH
                + "-refs/heads/master@{#}");
    assertThat(p.errors)
        .containsExactly(
            "Invalid Cr-Branched-From footer value", "Invalid Cr-Commit-Position footer value");
  }

  @Test
  public void messagesWithGarbage() throws Exception {
    PositionFooters p =
        extract(
            "A\n\n"
                + "Cr-Commit-Position: refs/head/master@{#2} garbage here\n"
                + "Cr-Branched-From: garbage here "
                + HASH
                + "-refs/heads/master@{#1}");
    assertThat(p.errors)
        .containsExactly(
            "Invalid Cr-Branched-From footer value", "Invalid Cr-Commit-Position footer value");
  }

  PositionFooters extract(String message) throws Exception {
    return PositionFooters.extract(mkRevCommit(message));
  }

  /** Validates assumptions on internal Gerrit implementation of footer parsing. */
  @Test
  public void ensureGetFooterLinesFetchesOnlyLastParagraph() throws Exception {
    assertThat(mkRevCommit("Not-Footer: indeed").getFooterLines()).hasSize(0);
    assertThat(mkRevCommit("First\n\nFooter: yep").getFooterLines()).hasSize(1);

    RevCommit commit = mkRevCommit("First\n\nIs-Footer: no\nNeither-Is: this\n\nFooter: yes");
    assertThat(commit.getFooterLines()).hasSize(1);
    assertThat(commit.getFooterLines("Footer")).hasSize(1);
  }
}

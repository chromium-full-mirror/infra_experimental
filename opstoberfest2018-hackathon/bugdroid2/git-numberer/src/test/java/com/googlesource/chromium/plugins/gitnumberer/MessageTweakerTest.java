// Copyright 2016 The Chromium Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

package com.googlesource.chromium.plugins.gitnumberer;

import static com.google.common.truth.Truth.assertThat;

import com.google.common.base.Joiner;
import org.junit.Test;

public class MessageTweakerTest extends AbstractRevWalkTest {

  @Test
  public void specialCases() throws Exception {
    new TestBuilder().assertExpected("", "");
    new TestBuilder("").assertExpected("", "");
    new TestBuilder("", "").assertExpected("", "");
  }

  @Test
  public void simple() throws Exception {
    new TestBuilder("Title").assertExpected("Title", "");
    new TestBuilder("Title", "", "Paragraph").assertExpected("Title", "", "Paragraph", "");
    new TestBuilder("Title", "", "Paragraph", "", "Footer: value")
        .assertExpected("Title", "", "Paragraph", "", "Footer: value");
  }

  @Test
  public void footersValueLeftTrim() throws Exception {
    new TestBuilder(
            "Title could be anything",
            "",
            "Footer:    @ note the many spaces before '@' which disappear")
        .assertExpected(
            "Title could be anything",
            "",
            "Footer: @ note the many spaces before '@' which disappear");
  }

  @Test
  public void footersWithNonFooters() throws Exception {
    new TestBuilder(
            "Title could be anything", "", "Footer: ok", "not well formed footer", "Well: formed.")
        .assertExpected(
            "Title could be anything",
            "",
            "not well formed footer",
            "",
            "Footer: ok",
            "Well: formed.");
  }

  @Test
  public void footersWithNonFootersCherryPick() throws Exception {
    new TestBuilder(
            "Title could be anything",
            "",
            "Change-Id: Ixxx",
            "(cherry picked from commit deadbeaf)")
        .assertExpected(
            "Title could be anything",
            "",
            "(cherry picked from commit deadbeaf)",
            "",
            "Change-Id: Ixxx");
  }

  @Test
  public void modifyWithOriginal() throws Exception {
    new TestBuilder(
            "Title could be anything",
            "",
            "Change-Id: Ixxx",
            "Cr-Commit-Position: don't do it yourself")
        .assertExpected(
            "Title could be anything",
            "",
            "Change-Id: Ixxx",
            "Cr-Original-Commit-Position: don't do it yourself");
  }

  @Test
  public void modifyWithOriginalCherryPick() throws Exception {
    new TestBuilder(
            "Title could be anything",
            "",
            "Change-Id: Ixxx",
            "Cr-Commit-Position: refs/heads/master@{#1}",
            "(cherry picked from commit deadbeaf)")
        .assertExpected(
            "Title could be anything",
            "",
            "(cherry picked from commit deadbeaf)",
            "",
            "Change-Id: Ixxx",
            "Cr-Original-Commit-Position: refs/heads/master@{#1}");
  }

  static class TestBuilder {
    String commitMessage;

    public TestBuilder(String... lines) throws Exception {
      commitMessage = Joiner.on("\n").join(lines);
    }

    public void assertExpected(String... lines) throws Exception {
      assertThat(MessageTweaker.copyAndModifyingFooters(commitMessage).toString())
          .isEqualTo(Joiner.on("\n").join(lines));
    }
  }
}

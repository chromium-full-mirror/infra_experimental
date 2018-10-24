// Copyright 2016 The Chromium Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

package com.googlesource.chromium.plugins.gitnumberer;

import static com.google.common.truth.Truth.assertThat;

import com.google.common.base.Joiner;
import java.io.UnsupportedEncodingException;
import java.util.ArrayList;
import java.util.List;
import org.eclipse.jgit.revwalk.FooterLine;
import org.eclipse.jgit.revwalk.RevCommit;
import org.junit.Test;

/**
 * Test-based documentation of findings about {@link RevCommit#getFooterLines}
 *
 * <p>If any of these starts failing, the logic of {@link Generator} might have to be changed.
 */
public class GetFooterLinesTest extends AbstractRevWalkTest {

  @Test
  public void obvious() throws Exception {
    assertThat(getFooters("Title", "", "Foo: ter")).containsExactly("Foo: ter").inOrder();
  }

  @Test
  public void cherryPick() throws Exception {
    assertThat(getFooters("Title", "", "Foo: ter", "(cherry picked from commit deadbeaf)"))
        .containsExactly("Foo: ter")
        .inOrder();
  }

  @Test
  public void lastAndFirstParagraph() throws Exception {
    assertThat(
            getFooters(
                "First-Line: is never a footer",
                "Foo: ter",
                "1-is: also a footer",
                "but this line isn't."))
        .containsExactly("Foo: ter", "1-is: also a footer")
        .inOrder();
  }

  ArrayList<String> getFooters(String... lines) throws UnsupportedEncodingException {
    List<FooterLine> footers = mkRevCommit(Joiner.on("\n").join(lines)).getFooterLines();
    ArrayList<String> actualFooters = new ArrayList<>(footers.size());
    for (FooterLine f : footers) actualFooters.add(f.getKey() + ": " + f.getValue());
    return actualFooters;
  }
}

/**
 * This code is derived from RevCommit and FotterLine classes of JGit.
 *
 * <p>Copyright (C) 2008-2009, Google Inc. Copyright (C) 2008, Shawn O. Pearce <spearce@spearce.org>
 * and other copyright owners as documented in the project's IP log.
 *
 * <p>This program and the accompanying materials are made available under the terms of the Eclipse
 * Distribution License v1.0 which accompanies this distribution, is reproduced below, and is
 * available at http://www.eclipse.org/org/documents/edl-v10.php
 *
 * <p>All rights reserved.
 *
 * <p>Redistribution and use in source and binary forms, with or without modification, are permitted
 * provided that the following conditions are met:
 *
 * <p>- Redistributions of source code must retain the above copyright notice, this list of
 * conditions and the following disclaimer.
 *
 * <p>- Redistributions in binary form must reproduce the above copyright notice, this list of
 * conditions and the following disclaimer in the documentation and/or other materials provided with
 * the distribution.
 *
 * <p>- Neither the name of the Eclipse Foundation, Inc. nor the names of its contributors may be
 * used to endorse or promote products derived from this software without specific prior written
 * permission.
 *
 * <p>THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR
 * IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND
 * FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR
 * CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
 * DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
 * DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
 * WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY
 * WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 */
package com.googlesource.chromium.plugins.gitnumberer;

import static java.nio.charset.StandardCharsets.UTF_8;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.OutputStreamWriter;
import java.nio.charset.Charset;
import java.util.ArrayList;
import java.util.Collections;
import org.eclipse.jgit.revwalk.RevCommit;
import org.eclipse.jgit.util.RawParseUtils;

// TODO(tandrii): consider upstreaming this to JGit repo.

public class MessageTweaker {
  /**
   * Copies the existing message and all its footers into new {@link StringBuilder}.
   *
   * <p>3 PostConditions:
   *
   * <p>1. If there is "(cherry picked from ...)" last non-empty line, then all existing footers are
   * moved after it in a new paragraph.
   *
   * <p>2. All footers starting with {@link PositionFooters#PREFIX} are modified to start with
   * {@link PositionFooters#PREFIX} + {@link PositionFooters#ORIGINAL} instead.
   *
   * <p>3. New footer lines can be appended to the returned {@link StringBuilder} directly like:
   * "\nExtra: footer".
   */
  public static StringBuilder copyAndModifyingFooters(String commitMessage) {
    return new MessageTweaker(commitMessage).copyAndModifyingFooters();
  }

  final byte[] raw;
  final Charset enc;
  final int msgB;
  final ArrayList<FooterLine> footers;
  final boolean lastParagraphHasNonFooters;

  /** Based on {@link org.eclipse.jgit.revwalk.FooterLine} */
  final class FooterLine {
    private final int keyStart;
    private final int keyEnd;
    private final int valStart;
    private final int valEnd;

    FooterLine(final int ks, final int ke, final int vs, final int ve) {
      keyStart = ks;
      keyEnd = ke;
      valStart = vs;
      valEnd = ve;
    }

    public String getKey() {
      return RawParseUtils.decode(enc, raw, keyStart, keyEnd);
    }

    public String getValue() {
      return RawParseUtils.decode(enc, raw, valStart, valEnd);
    }
  }

  /**
   * Parses footers of the commit's message in an efficient manner.
   *
   * <p>Based on a {@link RevCommit#getFooterLines}.
   */
  protected MessageTweaker(String currentMessage) {
    try (ByteArrayOutputStream os = new ByteArrayOutputStream();
        OutputStreamWriter w = new OutputStreamWriter(os, UTF_8); ) {
      w.write(currentMessage);
      w.flush();
      this.raw = os.toByteArray();
    } catch (IOException e) {
      throw new IllegalStateException("failed to encode message as UTF_8", e);
    }
    this.footers = new ArrayList<>(4);
    this.enc = UTF_8;
    this.msgB = 0;
    this.lastParagraphHasNonFooters = parse();
  }

  protected boolean parse() {
    // This is a copy of commit.getFooterLines() of JGit which also remembers
    // if there were any not well formed footers.
    int ptr = raw.length - 1;
    // Trim any trailing LFs, not interesting.
    while (ptr >= 0 && raw[ptr] == '\n') {
      ptr--;
    }

    boolean malformedFooters = false;
    for (; ; ) {
      ptr = RawParseUtils.prevLF(raw, ptr);
      if (ptr <= msgB) break; // Don't parse commit headers as footer lines.

      final int keyStart = ptr + 2;
      if (raw[keyStart] == '\n') break; // Stop at first paragraph break, no footers above it.

      final int keyEnd = RawParseUtils.endOfFooterLineKey(raw, keyStart);
      if (keyEnd < 0) {
        malformedFooters = true;
        continue; // Not a well formed footer line, skip it.
      }

      // Skip over the ': *' at the end of the key before the value.
      //
      int valStart = keyEnd + 1;
      while (valStart < raw.length && raw[valStart] == ' ') valStart++;

      // Value ends at the LF, and does not include it.
      int valEnd = RawParseUtils.nextLF(raw, valStart);
      if (raw[valEnd - 1] == '\n') valEnd--;
      footers.add(new FooterLine(keyStart, keyEnd, valStart, valEnd));
    }
    Collections.reverse(this.footers);
    return malformedFooters;
  }

  protected StringBuilder copyAndModifyingFooters() {
    StringBuilder sb = new StringBuilder();

    // If last paragraph has malformed footers, depot_tools' git_footers.py
    // won't be able to parse them. So, move all properly formed footers out
    // and insert as a new last paragraph.
    boolean moveoutFooters = this.lastParagraphHasNonFooters;

    int from = this.msgB;
    for (FooterLine f : footers) {
      // Copy stuff before footer starts, which includes at least one LF,
      // because it's a footer.
      sb.append(RawParseUtils.decode(enc, raw, from, f.keyStart));
      from = f.valEnd;
      if (!moveoutFooters) copyModifyFooter(sb, f);
      else {
        // This is either the very last line in commit message, or ends with LF,
        // which should be moved out as well.
        from++;
      }
    }
    // Copy anything after last valid footer but excluding empty lines.
    int to = raw.length;
    while (from < to && raw[to - 1] == '\n') to--;
    if (from < to) sb.append(RawParseUtils.decode(enc, raw, from, to));
    if (footers.isEmpty()) return ensureEndsWithNewParagraph(sb);
    if (!moveoutFooters) return sb;

    ensureEndsWithNewParagraph(sb);
    for (FooterLine f : footers) {
      sb.append('\n');
      copyModifyFooter(sb, f);
    }
    return sb;
  }

  /**
   * Copies footer, modifying if necessary its key on the fly.
   *
   * <p>Doesn't insert LF character at the end.
   */
  private void copyModifyFooter(StringBuilder sb, FooterLine f) {
    String key = f.getKey();
    if (key.startsWith(PositionFooters.PREFIX)) {
      sb.append(PositionFooters.PREFIX)
          .append(PositionFooters.ORIGINAL)
          .append(key.substring(PositionFooters.PREFIX.length()));
    } else {
      sb.append(key);
    }
    sb.append(": ").append(f.getValue());
  }

  private StringBuilder ensureEndsWithNewParagraph(StringBuilder sb) {
    int l = sb.length();
    if (l == 0 || sb.charAt(l - 1) != '\n') return sb.append('\n');
    return sb;
  }
}

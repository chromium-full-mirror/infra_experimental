// Copyright 2016 The Chromium Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

package com.googlesource.chromium.plugins.gitnumberer;

import com.google.gerrit.reviewdb.client.RefNames;
import java.util.regex.Pattern;

public class RefGlobMatcher {

  /** What characters are allowed in ref regex. This code only supports * globs. */
  static final Pattern REGEX_ALLOWED = Pattern.compile("^[-\\w/\\.\\*]+$");

  /** Ensures simple ref globs whose only pattern can be *. */
  public static boolean isValidGlob(String glob) {
    return REGEX_ALLOWED.matcher(glob).matches();
  }

  /** Translates glob which may contain several * patterns into Java regex. */
  static String translate(String glob) {
    StringBuilder sb = new StringBuilder(2 * glob.length());
    for (int i = 0; i < glob.length(); i++) {
      switch (glob.charAt(i)) {
        case '.':
          sb.append("\\.");
          break;
        case '*':
          sb.append(".*");
          break;
        default:
          sb.append(glob.charAt(i));
      }
    }
    return sb.toString();
  }

  /**
   * Matches refName against globs until it matches.
   *
   * @param refName
   * @param globs
   * @return true if {@link RefNames} matches at least one of globs.
   */
  public static boolean matches(String refName, String[] globs) {
    for (String glob : globs) {
      if (!isValidGlob(glob)) continue;
      if (Pattern.matches(translate(glob), refName)) return true;
    }
    return false;
  }
}

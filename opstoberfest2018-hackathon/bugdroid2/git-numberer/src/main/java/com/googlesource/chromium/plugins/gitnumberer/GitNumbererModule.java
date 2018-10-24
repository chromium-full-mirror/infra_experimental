// Copyright 2016 The Chromium Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

package com.googlesource.chromium.plugins.gitnumberer;

import com.google.gerrit.extensions.annotations.Exports;
import com.google.gerrit.extensions.api.projects.ProjectConfigEntryType;
import com.google.gerrit.extensions.registration.DynamicSet;
import com.google.gerrit.reviewdb.client.RefNames;
import com.google.gerrit.server.config.ProjectConfigEntry;
import com.google.gerrit.server.git.ChangeMessageModifier;
import com.google.gerrit.server.git.validators.OnSubmitValidationListener;
import com.google.gerrit.server.git.validators.RefOperationValidationListener;
import com.google.gerrit.server.util.MagicBranch;
import com.google.inject.AbstractModule;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class GitNumbererModule extends AbstractModule {
  private static final Logger log = LoggerFactory.getLogger(CommitValidator.class);

  static boolean isRefEnabled(
      String ref, String op, String[] enabledRefGlobs, String[] disabledRefGlobs) {
    // Never block uploading of any patches, drafts, and pushing changes to
    // project config at refs/meta/config regardless of this plugin config.
    // This is a safeguard so that plugin can be disabled at all times by
    // administrators in case it malfunctions.
    // TODO(tandrii): changes to project config will also pass through here.
    // Consider validating this plugin's project config if it has been modified.
    // For now, isEnabled() completely skips refs/meta/config changes.
    if (RefNames.REFS_CONFIG.equals(ref)
        || MagicBranch.isMagicBranch(ref)
        || ref.startsWith(RefNames.REFS_CHANGES)) {
      log.info(
          "skipping {} on {} because it is magic or {} or a new change patchset",
          op,
          ref,
          RefNames.REFS_CONFIG);
      return false;
    }

    if (RefGlobMatcher.matches(ref, disabledRefGlobs)) {
      log.info("skipping {} on {} because it's in disabled refs {}", op, ref, disabledRefGlobs);
      return false;
    }

    if (RefGlobMatcher.matches(ref, enabledRefGlobs)) {
      return true;
    }
    log.info("skipping {} on {} because it is not in enabled refs {}", op, ref, enabledRefGlobs);
    return false;
  }

  @Override
  protected void configure() {
    // Validate new commits pushed bypassing codereview.
    DynamicSet.bind(binder(), RefOperationValidationListener.class)
        .to(GitNumberFooterVerifier.class);
    // Validate new commits from submitting codereview changes.
    DynamicSet.bind(binder(), OnSubmitValidationListener.class).to(GitNumberFooterVerifier.class);
    // Generate new commit messages when submitting codereview changes.
    DynamicSet.bind(binder(), ChangeMessageModifier.class).to(GitNumberFooterGenerator.class);

    bind(ProjectConfigEntry.class)
        .annotatedWith(Exports.named(ConfigFields.VALIDATE_DISABLED))
        .toInstance(
            new ProjectConfigEntry(
                "Disable validation on refs",
                null,
                ProjectConfigEntryType.ARRAY,
                null,
                false,
                "Array of ref globs on which validation is disabled. "
                    + "Takes priority over enabled."));
    bind(ProjectConfigEntry.class)
        .annotatedWith(Exports.named(ConfigFields.VALIDATE_ENABLED))
        .toInstance(
            new ProjectConfigEntry(
                "Enable validation on refs",
                null,
                ProjectConfigEntryType.ARRAY,
                null,
                false,
                "Array of ref globs on which validation is enabled"));

    bind(ProjectConfigEntry.class)
        .annotatedWith(Exports.named(ConfigFields.GENERATE_DISABLED))
        .toInstance(
            new ProjectConfigEntry(
                "Disable generation on refs",
                null,
                ProjectConfigEntryType.ARRAY,
                null,
                false,
                "Array of ref globs on which generation is disabled. "
                    + "Takes priority over enabled."));
    bind(ProjectConfigEntry.class)
        .annotatedWith(Exports.named(ConfigFields.GENERATE_ENABLED))
        .toInstance(
            new ProjectConfigEntry(
                "Enable generation on refs",
                null,
                ProjectConfigEntryType.ARRAY,
                null,
                false,
                "Array of ref globs on which generation is enabled"));
  }
}

// Copyright 2017 The Chromium Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

package com.googlesource.chromium.plugins.gitnumberer;

import com.google.gerrit.extensions.annotations.PluginName;
import com.google.gerrit.reviewdb.client.Branch;
import com.google.gerrit.reviewdb.client.Project;
import com.google.gerrit.server.config.PluginConfig;
import com.google.gerrit.server.git.ChangeMessageModifier;
import com.google.gerrit.server.project.NoSuchProjectException;
import com.google.inject.Inject;
import org.eclipse.jgit.revwalk.RevCommit;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class GitNumberFooterGenerator implements ChangeMessageModifier {
  private static final Logger log = LoggerFactory.getLogger(GitNumberFooterGenerator.class);
  @Inject private com.google.gerrit.server.config.PluginConfigFactory cfg;
  @Inject private @PluginName String pluginName;

  @Override
  public String onSubmit(
      String newCommitMessage,
      RevCommit original,
      RevCommit baseCommit,
      Branch.NameKey destination) {

    Project.NameKey project = destination.getParentKey();
    PluginConfig pluginConfig = null;
    try {
      pluginConfig = cfg.getFromProjectConfig(project, pluginName);
    } catch (NoSuchProjectException e) {
      String msg = "Can't fetch config for project " + project;
      log.error(msg);
      throw new IllegalStateException(msg, e);
    }
    if (!Generator.isEnabled(destination.get(), pluginConfig)) {
      return newCommitMessage;
    }

    if (baseCommit.getName() == null || original.getName() == null) {
      log.warn("baseCommit {} or original {} is null", baseCommit, original);
      return newCommitMessage;
    }
    if (baseCommit.getName().equals(original.getName())) {
      log.debug("same original {} and baseCommit {}", original, baseCommit);
      return newCommitMessage;
    }

    try {
      return Generator.childMessage(baseCommit, newCommitMessage, destination.get());
    } catch (GitNumberValidationError e) {
      log.info("{}, no generation", e.error);
      /*
       * This means that parent commit has invalid footers, which implies
       * something is misconfigured in either case by git admins.
       *
       * If validator is configured on the ref, then it will reject any updates
       * to this ref for the same reason (bad parent(ref's HEAD) footers).
       * Whoever enabled validator and generator on this ref should have checked
       * the HEAD first. This is extremely rare occasion in the currently
       * intended usage of this plugin, that it's totally fine to just let user,
       * who fails to submit a change, complain to the repository admin to
       * figure this out.
       */
      if (CommitValidator.isEnabled(destination.get(), pluginConfig)) {
        return newCommitMessage;
      }
      /*
       * Else, validator is not configured, which is against instructions for
       * Git Numberer usage. In this case, Generating footers is pointless and
       * potentially harmful. Throwing InvalidState will result in internal
       * server error (500) for submitting user PoV, which is not ideal, but
       * once user escalates the issue, it'd be obvious in the Gerrit logs.
       * Again this is extremely rare occasion in the currently intended usage,
       * so such handling should be adequate. If this becomes a fequent ocasion,
       * the ChangeMessageModifier.onSubmit could be extended to throw
       * validation exception which will be propagated to the user.
       * TODO(tandrii): consider doing this.
       */
      throw new IllegalStateException(
          "Bad parent commit's footers "
              + e.error
              + " and validator is not configured on ref "
              + destination.get()
              + ". Contact Git Admin.");
    }
  }
}

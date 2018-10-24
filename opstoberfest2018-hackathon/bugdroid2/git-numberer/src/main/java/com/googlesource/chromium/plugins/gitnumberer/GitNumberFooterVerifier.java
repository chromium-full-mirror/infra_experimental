// Copyright 2016 The Chromium Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

package com.googlesource.chromium.plugins.gitnumberer;

import com.google.gerrit.extensions.annotations.PluginName;
import com.google.gerrit.server.config.PluginConfig;
import com.google.gerrit.server.events.RefReceivedEvent;
import com.google.gerrit.server.git.GitRepositoryManager;
import com.google.gerrit.server.git.validators.OnSubmitValidationListener;
import com.google.gerrit.server.git.validators.RefOperationValidationListener;
import com.google.gerrit.server.git.validators.ValidationMessage;
import com.google.gerrit.server.project.NoSuchProjectException;
import com.google.gerrit.server.validators.ValidationException;
import com.google.inject.Inject;
import com.google.inject.Singleton;
import java.io.IOException;
import java.util.Collections;
import java.util.List;
import java.util.Optional;
import org.eclipse.jgit.errors.RepositoryNotFoundException;
import org.eclipse.jgit.lib.ObjectId;
import org.eclipse.jgit.lib.Ref;
import org.eclipse.jgit.lib.Repository;
import org.eclipse.jgit.revwalk.RevWalk;
import org.eclipse.jgit.transport.ReceiveCommand;
import org.eclipse.jgit.transport.ReceiveCommand.Type;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

@Singleton
class GitNumberFooterVerifier
    implements RefOperationValidationListener, OnSubmitValidationListener {

  private static final Logger log = LoggerFactory.getLogger(GitNumberFooterVerifier.class);

  @Inject private com.google.gerrit.server.config.PluginConfigFactory cfg;

  @Inject private @PluginName String pluginName;

  @Inject protected GitRepositoryManager repoManager;

  @Override
  public List<ValidationMessage> onRefOperation(RefReceivedEvent event) throws ValidationException {
    PluginConfig pluginConfig;
    try {
      pluginConfig = cfg.getFromProjectConfig(event.getProjectNameKey(), pluginName);
    } catch (NoSuchProjectException e) {
      throw new ValidationException(
          String.format("can't fetch config for project %s", event.getProjectNameKey().get()), e);
    }
    if (!CommitValidator.isEnabled(event.getRefName(), pluginConfig)) {
      return Collections.emptyList();
    }

    ObjectId currentTip = ObjectId.zeroId();
    switch (event.command.getType()) {
      case CREATE:
      case UPDATE:
        try (Repository repo = repoManager.openRepository(event.getProjectNameKey());
            RevWalk rw = new RevWalk(repo)) {
          if (event.command.getType() == Type.UPDATE) {
            currentTip = repo.exactRef(event.getRefName()).getObjectId();
          }
          CommitValidator.validateMany(
              r -> Optional.ofNullable(repo.exactRef(r)).map(Ref::getObjectId),
              rw,
              pluginConfig,
              event.getRefName(),
              currentTip,
              event.command.getNewId());
        } catch (RepositoryNotFoundException e) {
          throw new ValidationException("repository no longer exists", e);
        } catch (IOException e) {
          throw new ValidationException("failed to read commits", e);
        } catch (GitNumberValidationError e) {
          throw new ValidationException(e.error, e);
        }
        break;
      case UPDATE_NONFASTFORWARD:
        throw new ValidationException("non fast forward not allowed");
      case DELETE:
        break;
      default:
        // Maybe something new is in Gerrit core, don't silently let is pass
        // through.
        throw new ValidationException(
            String.format("unknown operation: %s", event.command.getType()));
    }
    return Collections.emptyList();
  }

  @Override
  public void preBranchUpdate(Arguments args) throws ValidationException {
    PluginConfig config;
    try {
      config = cfg.getFromProjectConfig(args.getProject(), pluginName);
    } catch (NoSuchProjectException e) {
      throw new ValidationException(e.getMessage(), e);
    }
    for (String refName : args.getCommands().keySet()) {
      if (!CommitValidator.isEnabled(refName, config)) {
        // This will skip refs/changes/xx/yyyy/<new-patchset-number>.
        continue;
      }
      ReceiveCommand cmd = args.getCommands().get(refName);
      try {
        log.info("validating submit into {}: {} .. {}", refName, cmd.getOldId(), cmd.getNewId());
        CommitValidator.validateMany(
            args::getRef, args.getRevWalk(), config, refName, cmd.getOldId(), cmd.getNewId());
      } catch (IOException e) {
        throw new ValidationException("failed to read commits", e);
      } catch (GitNumberValidationError e) {
        throw new ValidationException(e.error, e);
      }
    }
  }
}

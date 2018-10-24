// Copyright 2016 The Chromium Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

package com.googlesource.chromium.plugins.gitnumberer;

import static com.google.common.base.Preconditions.checkNotNull;
import static com.google.common.truth.Truth.assertThat;

import java.io.UnsupportedEncodingException;
import org.eclipse.jgit.api.Git;
import org.eclipse.jgit.lib.CommitBuilder;
import org.eclipse.jgit.lib.ObjectId;
import org.eclipse.jgit.lib.PersonIdent;
import org.eclipse.jgit.revwalk.RevCommit;
import org.eclipse.jgit.revwalk.RevWalk;
import org.junit.Ignore;
import org.junit.Rule;
import org.junit.rules.ExternalResource;
import org.junit.rules.TemporaryFolder;

/** Provides RevWalk based on Git repo in temp directory. */
@Ignore
public class AbstractRevWalkTest {
  static final PersonIdent FAKE_AUTHOR = new PersonIdent("a", "e");
  static final ObjectId FAKE_TREE_ID =
      ObjectId.fromString("9376e406706cec026841f36fae823d18bb9b3cd0");

  @Rule public TemporaryFolder tempDir = new TemporaryFolder();

  @Rule
  public ExternalResource gitFinalizer =
      new ExternalResource() {
        @Override
        protected void after() {
          if (rw != null) {
            rw.close();
            rw = null;
          }
          if (git != null) {
            git.close();
            git = null;
          }
        }
      };

  private Git git = null;
  private RevWalk rw = null;

  protected Git getGit() throws Exception {
    if (git == null) {
      git = Git.init().setDirectory(tempDir.newFolder()).call();
    }
    return git;
  }

  protected RevWalk getRevWalk() throws Exception {
    if (rw == null) {
      rw = new RevWalk(getGit().getRepository());
    }
    return rw;
  }

  protected RevCommit writeCommit(ObjectId parent, String message) throws Exception {
    checkNotNull(message);
    CommitBuilder cb = new CommitBuilder();
    cb.setMessage(message);
    cb.setAuthor(FAKE_AUTHOR);
    cb.setCommitter(FAKE_AUTHOR);
    if (parent != null) cb.setParentId(parent);
    cb.setTreeId(ObjectId.zeroId());
    ObjectId id = getGit().getRepository().newObjectInserter().insert(cb);
    return getRevWalk().parseCommit(id);
  }

  /**
   * Generates commit and optionally a parent with given messages.
   *
   * @param parentMessage if null, returned commit will have no parent.
   * @param message
   * @return commit object.
   * @throws Exception
   */
  protected RevCommit mkCommits(String parentMessage, String message) throws Exception {
    checkNotNull(message);

    RevCommit parent = null;
    if (parentMessage != null) {
      parent = writeCommit(null, parentMessage);
      message = message.replace("{}", parent.getName());
    }
    RevCommit commit = writeCommit(parent, message);
    assertThat(commit.getParentCount()).isEqualTo(parent == null ? 0 : 1);
    return commit;
  }

  /**
   * Generate RevParse object with just given message without attached RevWalk.
   *
   * <p>If you need RevWalk, use {@link #mkCommits} or {@link #writeCommit}.
   */
  public static RevCommit mkRevCommit(String message) throws UnsupportedEncodingException {
    CommitBuilder b = new CommitBuilder();
    // These 4 fields are minimum that are required for build() to work.
    b.setAuthor(FAKE_AUTHOR);
    b.setCommitter(FAKE_AUTHOR);
    b.setTreeId(FAKE_TREE_ID);
    b.setMessage(message);
    return RevCommit.parse(b.build());
  }
}

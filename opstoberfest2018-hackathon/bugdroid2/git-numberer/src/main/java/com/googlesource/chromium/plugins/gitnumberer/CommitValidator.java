// Copyright 2016 The Chromium Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

package com.googlesource.chromium.plugins.gitnumberer;

import static com.google.common.base.Preconditions.checkNotNull;
import static com.google.common.base.Preconditions.checkState;

import com.google.gerrit.server.config.PluginConfig;
import java.io.IOException;
import java.util.ArrayList;
import java.util.Iterator;
import java.util.List;
import java.util.Optional;
import org.eclipse.jgit.lib.ObjectId;
import org.eclipse.jgit.revwalk.RevCommit;
import org.eclipse.jgit.revwalk.RevSort;
import org.eclipse.jgit.revwalk.RevWalk;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/** Validates new commit objects from single ref's point of view. */
public class CommitValidator {
  private static final Logger log = LoggerFactory.getLogger(CommitValidator.class);

  static boolean isEnabled(String ref, PluginConfig pluginConfig) {
    return GitNumbererModule.isRefEnabled(
        ref,
        "validation",
        pluginConfig.getStringList(ConfigFields.VALIDATE_ENABLED),
        pluginConfig.getStringList(ConfigFields.VALIDATE_DISABLED));
  }

  static void validateMany(
      RefLookup refLookup,
      RevWalk walk,
      PluginConfig pluginConfig,
      String ref,
      ObjectId currentTip,
      ObjectId newTip)
      throws GitNumberValidationError, IOException {
    CommitWithExtractedFooters fromOtherBranch =
        validateWhileSameOriginatingBranch(walk, ref, currentTip, newTip);

    if (fromOtherBranch == null) {
      log.info("verified {} to be a valid orphan branch", ref);
      return;
    }
    if (!currentTip.equals(ObjectId.zeroId())) {
      throw new GitNumberValidationError(
          "Cr-Commit-Position footer must be for "
              + ref
              + " in commit "
              + fromOtherBranch.commit.getName());
    }

    validateBranchingClaim(refLookup, walk, pluginConfig, fromOtherBranch);
  }

  /**
   * Verify the claim of a commit's footer to be fromOtherBranch by checking that
   *
   * <ul>
   *   <li>the other branch indeed exists
   *   <li>this plugin is enabled on the other branch (otherwise it's easy to accidentally "cheat")
   *   <li>the other branch contains this commit.
   * </ul>
   */
  private static void validateBranchingClaim(
      RefLookup refLookup,
      RevWalk walk,
      PluginConfig pluginConfig,
      CommitWithExtractedFooters fromOtherBranch)
      throws GitNumberValidationError, IOException {

    if (!isEnabled(fromOtherBranch.getBranch(), pluginConfig)) {
      // TODO(tandrii): cover this by test case.
      throw new GitNumberValidationError(
          fromOtherBranch.error("which doesn't require valid footers"));
    }
    Optional<ObjectId> branch = refLookup.getRef(fromOtherBranch.getBranch());
    if (!branch.isPresent()) {
      // TODO(tandrii): cover this by test case.
      throw new GitNumberValidationError(fromOtherBranch.error("which doesn't exist"));
    }
    if (!walk.isMergedInto(fromOtherBranch.commit, walk.parseCommit(branch.get()))) {
      throw new GitNumberValidationError(fromOtherBranch.error("which doesn't contain the commit"));
    }
  }

  interface RefLookup {
    Optional<ObjectId> getRef(String name) throws IOException;
  }

  static class CommitWithExtractedFooters {
    RevCommit commit;
    PositionFooters footers;

    public CommitWithExtractedFooters(RevCommit commit, PositionFooters footers) {
      this.commit = commit;
      this.footers = footers;
    }

    public String getBranch() {
      return this.footers.position.branch;
    }

    public String error(String suffix) {
      return "commit " + commit.getName() + " claims to be from " + getBranch() + ' ' + suffix;
    }
  }

  /**
   * Validates all commits in RevWalk while they originate on a given branch according to
   * Cr-Commit-Position footer.
   *
   * @param newTip
   * @param currentTip
   * @return first commit and its extracted footers from different branch or null if there is no
   *     such commit in RevWalk.
   */
  private static CommitWithExtractedFooters validateWhileSameOriginatingBranch(
      RevWalk walk, String branch, ObjectId currentTip, ObjectId newTip)
      throws GitNumberValidationError, IOException {
    walk.reset();
    walk.sort(RevSort.NONE);
    walk.markStart(walk.parseCommit(newTip));

    // Iterate over all new commits originating on current ref by their position
    // footers but stop checking at this branch HEAD if it already exists.
    if (!currentTip.equals(ObjectId.zeroId())) {
      walk.markUninteresting(walk.parseCommit(currentTip));
    }
    for (RevCommit commit; (commit = walk.next()) != null; ) {
      walk.parseBody(commit);
      PositionFooters pf = PositionFooters.extract(commit);
      if (!pf.errors.isEmpty()) throw new GitNumberValidationError(pf.formatErrors(null));
      if (!pf.position.branch.equals(branch)) return new CommitWithExtractedFooters(commit, pf);
      // Commit originated on this branch, so check against its parent.
      RevCommit parent = null;
      if (commit.getParentCount() > 0) {
        // TODO(tandrii): cover this by test case.
        parent = commit.getParent(0);
        walk.parseBody(parent);
      }
      /*
       * TODO(tandrii): this isn't the most efficient way because we are
       * extracting footers up to 3 times per commit. Consider improving it.
       */
      CommitValidator.validate(walk, commit, branch);
    }
    return null;
  }

  /**
   * Validates position footers of a given commit and its will-be parent if any.
   *
   * <p>Note that parent may not necessarily itself be on destination branch. In general, one commit
   * can be on many different branches. However, Validator can figure out which branch parent commit
   * landed originally by looking at the parent's commit position footers.
   *
   * @param walk RevWalk object to fetch parent if necessary.
   * @param commit from the same RevWalk object.
   * @param destBranch full ref name of destination branch onto which commit is being merged or
   *     landed to.
   * @throws GitNumberValidationError if validation fails.
   * @throws IOException if RevWalk doesn't contain commit or its parent.
   */
  public static void validate(RevWalk walk, RevCommit commit, String destBranch)
      throws GitNumberValidationError, IOException {
    if (commit.getRawBuffer() == null) walk.parseBody(commit);
    switch (commit.getParentCount()) {
      case 0:
        // First commit on an orphan branch must have just initial position.
        validateCommitFooters(commit, destBranch, PositionFooters.INITIAL_POSITION, null);
        return;
      case 1:
        RevCommit parent = commit.getParent(0);
        walk.parseBody(parent);
        log.debug("validating {} with 1 parent {}", commit, parent);
        PositionFooters pFooters = extractAndValidateParentFooters(parent);
        checkState(pFooters.position != null);
        if (destBranch.equals(pFooters.position.branch)) {
          // The same branch for parent and this commit, and the same lineage.
          validateCommitFooters(
              commit, destBranch, pFooters.position.number + 1, pFooters.branchedFrom);
        } else {
          // New commit is on a new branch, and so should have 1 extra lineage
          // comparing to parent branch.
          // Note: lineage is ordered here bottom-up, thus appending to lineage
          // list means expecting new entry to be above those inherited from the
          // parent in the (child) commit message.
          ArrayList<BranchedFromValue> lineage = new ArrayList<>(pFooters.branchedFrom);
          lineage.add(
              new BranchedFromValue(
                  parent.getName(), pFooters.position.branch, pFooters.position.number));
          validateCommitFooters(commit, destBranch, PositionFooters.INITIAL_POSITION, lineage);
        }
        return;
      default:
        throw new GitNumberValidationError("merge commit " + commit.getName() + " not allowed");
    }
  }

  private static PositionFooters extractAndValidateParentFooters(RevCommit parent)
      throws GitNumberValidationError {
    PositionFooters extracted = PositionFooters.extract(parent);
    if (!extracted.errors.isEmpty()) {
      throw new GitNumberValidationError(extracted.formatErrors(parent));
    }
    checkNotNull(extracted.position);
    return extracted;
  }

  private static void validateCommitFooters(
      RevCommit commit,
      String destBranch,
      int expectedNumber,
      List<BranchedFromValue> expectedLineage)
      throws GitNumberValidationError {
    PositionFooters extracted = PositionFooters.extract(commit);
    if (!extracted.errors.isEmpty()) {
      throw new GitNumberValidationError(extracted.formatErrors(null));
    }
    checkNotNull(extracted.position);
    if (!extracted.position.branch.equals(destBranch)) {
      throw new GitNumberValidationError(
          PositionFooters.COMMIT_POSITION + " footer must be for " + destBranch);
    }
    if (extracted.position.number != expectedNumber) {
      throw new GitNumberValidationError(
          PositionFooters.COMMIT_POSITION + " footer must have position number " + expectedNumber);
    }
    if (expectedLineage != null) {
      if (!matchingLineage(extracted.branchedFrom, expectedLineage))
        throw new GitNumberValidationError(
            "invalid lineage footers " + PositionFooters.BRANCHED_FROM);
    } else if (!extracted.branchedFrom.isEmpty()) {
      throw new GitNumberValidationError(
          PositionFooters.BRANCHED_FROM + " not allowed in the first commit of orphan branch");
    }
  }

  private static boolean matchingLineage(
      List<BranchedFromValue> given, List<BranchedFromValue> expected) {
    Iterator<BranchedFromValue> givenIterator = given.iterator();
    for (BranchedFromValue e : expected) {
      if (!givenIterator.hasNext() || !e.equals(givenIterator.next())) return false;
    }
    return !givenIterator.hasNext();
  }
}

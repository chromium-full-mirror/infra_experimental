// Copyright 2016 The Chromium Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

package com.googlesource.chromium.plugins.gitnumberer;

import static com.google.common.truth.Truth.assertThat;
import static com.google.gerrit.extensions.client.ListChangesOption.SUBMITTABLE;
import static org.junit.Assert.fail;

import com.google.gerrit.acceptance.GitUtil;
import com.google.gerrit.acceptance.PushOneCommit;
import com.google.gerrit.extensions.api.changes.SubmitInput;
import com.google.gerrit.extensions.client.ChangeStatus;
import com.google.gerrit.extensions.common.ChangeInfo;
import com.google.gerrit.extensions.restapi.ResourceConflictException;
import com.google.gerrit.extensions.restapi.RestApiException;
import org.eclipse.jgit.revwalk.RevCommit;
import org.eclipse.jgit.transport.PushResult;
import org.eclipse.jgit.transport.RemoteRefUpdate;
import org.junit.Test;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class GitNumberFooterVerfierIT extends LightweightWithConfigIT {
  private static final Logger log = LoggerFactory.getLogger(GitNumberFooterVerfierIT.class);

  // Merge (land change) tests =================================================

  @Test
  public void mergeInvalidParentMissingFooter() throws Exception {
    initWithEmptyCommit();
    assertEnabledPlugin("refs/heads/master");

    PushOneCommit.Result change =
        createChange("Valid Child\n\nCr-Commit-Position: refs/heads/master@{#2}", "master");
    change.assertOkStatus();
    submit(
        change.getChangeId(),
        ResourceConflictException.class,
        "Cr-Commit-Position footer is required in parent commit \\p{Alnum}{40}");
  }

  @Test
  public void mergeInvalidChangeMissingFooter() throws Exception {
    initWithGoodParent();
    assertEnabledPlugin("refs/heads/master");

    PushOneCommit.Result change = createChange("Missing footer", "master");
    change.assertOkStatus();
    submit(
        change.getChangeId(),
        ResourceConflictException.class,
        "Cr-Commit-Position footer is required");
  }

  @Test
  public void mergeValidSimple() throws Exception {
    initWithGoodParent();
    assertEnabledPlugin("refs/heads/master");

    PushOneCommit.Result change =
        createChange("A\n\nCr-Commit-Position: refs/heads/master@{#2}", "master");
    change.assertOkStatus();
    submit(change.getChangeId(), null, null);
  }

  @Test
  public void mergeInvalidNewBranchWrongLineage() throws Exception {
    initWithGoodParent();
    assertEnabledPlugin("refs/heads/branch");

    PushOneCommit.Result change =
        createChange(
            "A\n\n"
                + "Cr-Commit-Position: refs/heads/branch@{#1}\n"
                + "Cr-Branched-From: "
                + getRemoteHead().getName()
                + "-refs/heads/wrong@{#1}",
            "branch");
    change.assertOkStatus();
    submit(
        change.getChangeId(),
        ResourceConflictException.class,
        "invalid lineage footers Cr-Branched-From");
  }

  @Test
  public void mergeInvalidNewBranchWrongPosition() throws Exception {
    RevCommit parent = initWithGoodParent();
    assertEnabledPlugin("refs/heads/branch");

    PushOneCommit.Result change =
        createChange(
            "2\n\n"
                + "Cr-Commit-Position: refs/heads/master@{#2}\n"
                + "Cr-Branched-From: "
                + parent.getName()
                + "-refs/heads/master@{#1}",
            "branch");
    change.assertOkStatus();
    submit(
        change.getChangeId(),
        ResourceConflictException.class,
        "Cr-Commit-Position footer must be for refs/heads/branch");
  }

  @Test
  public void mergeValidNewBranch() throws Exception {
    RevCommit parent = initWithGoodParent();
    assertEnabledPlugin("refs/heads/branch");

    PushOneCommit.Result change =
        createChange(
            "A\n\n"
                + "Cr-Commit-Position: refs/heads/branch@{#1}\n"
                + "Cr-Branched-From: "
                + parent.getName()
                + "-refs/heads/master@{#1}",
            "branch");
    change.assertOkStatus();
    submit(change.getChangeId(), null, null);
  }

  @Test
  public void mergeValidNotConfigured() throws Exception {
    initWithGoodParent();
    assertDisabledPlugin("refs/heads/infra/config");
    PushOneCommit.Result change = createChange("Whatever", "infra/config");
    change.assertOkStatus();
    submit(change.getChangeId(), null, null);
  }

  // Push tests ==========================================================

  @Test
  public void pushSingleBranch() throws Exception {
    // Tests single branch with 5 commits.
    // First_{#1} -> Second_{#2} -> Third_n/a -> Fourth_{#14} -> Fifth_{#15}.
    // Plugin enabled: YES  ->   NO   ->      NO       ->     YES.
    project = createProject("empty", null, false);
    testRepo = cloneProject(project);

    configurePlugin("refs/heads/master");
    PushOneCommit.Result first =
        prepareOneCommit("Start of master branch\n\nCr-Commit-Position: refs/heads/master@{#1}")
            .to("refs/heads/master");
    first.assertOkStatus();
    PushOneCommit.Result second =
        prepareOneCommit("2nd on master branch\n\nCr-Commit-Position: refs/heads/master@{#2}")
            .to("refs/heads/master");
    second.assertOkStatus();

    PushOneCommit third = prepareOneCommit("3nd on master branch");
    PushOneCommit.Result attempt1 = third.to("refs/heads/master");
    attempt1.assertErrorStatus();
    assertThat(attempt1.getMessage()).contains("Cr-Commit-Position footer is required");

    disablePlugin();
    PushOneCommit.Result attempt2 = third.to("refs/heads/master");
    attempt2.assertOkStatus();

    configurePlugin("refs/heads/master");
    PushOneCommit fourth =
        prepareOneCommit(
            "4th after bad parent.\n\n" + "Cr-Commit-Position: refs/heads/master@{#14}");
    attempt1 = fourth.to("refs/heads/master");
    attempt1.assertErrorStatus();
    assertThat(attempt1.getMessage())
        .contains(
            "Cr-Commit-Position footer is required in parent commit "
                + attempt2.getCommit().getName());

    disablePlugin();
    attempt2 = fourth.to("refs/heads/master");
    attempt2.assertOkStatus();

    configurePlugin("refs/heads/not-master");
    PushOneCommit.Result fifth =
        prepareOneCommit("Only parent matters.\n\nCr-Commit-Position: refs/heads/master@{#15}")
            .to("refs/heads/master");
    fifth.assertOkStatus();
  }

  @Test
  public void pushBranchingAllowed() throws Exception {
    // Tests that verification is only ran on new commits
    project = createProject("empty", null, false);
    testRepo = cloneProject(project);
    configurePlugin("refs/heads/*");

    assertEnabledPlugin("refs/heads/master");
    PushOneCommit.Result first =
        prepareOneCommit("1st\n\nCr-Commit-Position: refs/heads/master@{#1}")
            .to("refs/heads/master");
    first.assertOkStatus();
    PushOneCommit.Result second =
        prepareOneCommit("2nd\n\nCr-Commit-Position: refs/heads/master@{#2}")
            .to("refs/heads/master");
    second.assertOkStatus();

    // Push these commits to another branch, not enabled in plugin.
    assertDisabledPlugin("refs/heads/disabled");
    PushResult result = GitUtil.pushHead(testRepo, "refs/heads/disabled");
    assertThat(result.getRemoteUpdate("refs/heads/disabled").getStatus())
        .named(result.getMessages())
        .isEqualTo(RemoteRefUpdate.Status.OK);

    // Push the same commits to a branch on which plugin is enabled.
    assertEnabledPlugin("refs/heads/branched");
    result = GitUtil.pushHead(testRepo, "refs/heads/branched");
    assertThat(result.getRemoteUpdate("refs/heads/branched").getStatus())
        .named(result.getMessages())
        .isEqualTo(RemoteRefUpdate.Status.OK);

    // Push the same commits + 1 new one to a branch on which plugin is enabled.
    assertEnabledPlugin("refs/heads/release");
    PushOneCommit.Result release =
        prepareOneCommit(
                "Release off master {#2}\n\n"
                    + "Cr-Commit-Position: refs/heads/release@{#1}\n"
                    + "Cr-Branched-From: "
                    + second.getCommit().getName()
                    + "-refs/heads/master@{#2}\n")
            .to("refs/heads/release");
    release.assertOkStatus();

    // But a new commit for release branch can't be pushed onto new branch
    // before release branch itself.
    assertEnabledPlugin("refs/heads/else");
    PushOneCommit.Result hotfix =
        prepareOneCommit(
                "Else on release\n\n"
                    + "Cr-Commit-Position: refs/heads/release@{#2}\n"
                    + "Cr-Branched-From: "
                    + second.getCommit().getName()
                    + "-refs/heads/master@{#2}\n")
            .to("refs/heads/else");
    assertThat(hotfix.getMessage())
        .contains(
            hotfix.getCommit().getName()
                + " claims to be from refs/heads/release "
                + "which doesn't contain the commit");

    // Do it right: first to release branch, then to else.
    assertEnabledPlugin("refs/heads/release");
    result = GitUtil.pushHead(testRepo, "refs/heads/release");
    assertThat(result.getRemoteUpdate("refs/heads/release").getStatus())
        .named(result.getMessages())
        .isEqualTo(RemoteRefUpdate.Status.OK);

    // Push to refs/heads/else should work now.
    assertEnabledPlugin("refs/heads/else");
    result = GitUtil.pushHead(testRepo, "refs/heads/else");
    assertThat(result.getRemoteUpdate("refs/heads/else").getStatus())
        .named(result.getMessages())
        .isEqualTo(RemoteRefUpdate.Status.OK);
  }

  @Test
  public void pushBackToMasterAfterBranching() throws Exception {
    /* Starting with
     *  master   A{master@1}
     *                      \
     *  other                B{other@1}
     * pushing B to master must be forbidden.
     */
    project = createProject("empty", null, false);
    testRepo = cloneProject(project);
    configurePlugin("refs/heads/master");
    PushOneCommit.Result first =
        prepareOneCommit("1st\n\nCr-Commit-Position: refs/heads/master@{#1}")
            .to("refs/heads/master");
    first.assertOkStatus();
    PushOneCommit.Result second =
        prepareOneCommit(
                "1st on other\n\nCr-Commit-Position: refs/heads/other@{#1}\n"
                    + "Cr-Branched-From: "
                    + first.getCommit().getName()
                    + "-refs/heads/master@{#1}")
            .to("refs/heads/other");
    second.assertOkStatus();

    // Push
    PushResult result = GitUtil.pushHead(testRepo, "refs/heads/master");
    assertThat(result.getRemoteUpdate("refs/heads/master").getStatus())
        .named(result.getMessages())
        .isEqualTo(RemoteRefUpdate.Status.REJECTED_OTHER_REASON);
    assertThat(result.getRemoteUpdate("refs/heads/master").getMessage())
        .contains("Cr-Commit-Position footer must be for refs/heads/master");
  }

  // Helpers =============================================================

  /**
   * On return, commit doesn't yet exist in testRepo.
   *
   * @return PushOneCommit that has be pushed for commit to be created.
   */
  PushOneCommit prepareOneCommit(String message) {
    log.info("creatingCommit: \n{}", message);
    return pushFactory.create(db, admin.getIdent(), testRepo, message, "file", message);
  }

  PushOneCommit.Result createChange(String message, String branch) throws Exception {
    if (!branch.equals("master")) {
      // Gerrit doens't allow git push HEAD:refs/for/not-yet-existing-branch.
      // So, create the branch first.
      PushResult r = GitUtil.pushHead(testRepo, "refs/heads/" + branch);
      GitUtil.assertPushOk(r, "refs/heads/" + branch);
    }
    PushOneCommit push =
        pushFactory.create(db, admin.getIdent(), testRepo, message, "file", "content");
    return push.to("refs/for/" + branch);
  }

  void initWithEmptyCommit() throws Exception {
    project = createProject("initialized", null, true);
    testRepo = cloneProject(project);

    configurePlugin();
  }

  RevCommit initWithGoodParent() throws Exception {
    project = createProject("empty", null, false);
    assertThat(getRemoteHead()).isNull();
    testRepo = cloneProject(project);
    PushOneCommit.Result first =
        prepareOneCommit("Start of master branch\n\nCr-Commit-Position: refs/heads/master@{#1}")
            .to("refs/heads/master");
    first.assertOkStatus();
    log.info(
        "Created initial commit {} with valid footers (remote: {})",
        first.getCommit(),
        getRemoteHead(project, "refs/heads/master"));
    // testRepo = cloneProject(project);
    assertThat(getRemoteHead()).isEqualTo(first.getCommit());
    configurePlugin();
    return first.getCommit();
  }

  void submit(
      String changeId,
      Class<? extends RestApiException> expectedExceptionType,
      String expectedExceptionMessagePattern)
      throws Exception {
    approve(changeId);
    assertThat(get(changeId, SUBMITTABLE).submittable)
        .named("submit bit on ChangeInfo")
        .isEqualTo(true);

    try {
      gApi.changes().id(changeId).current().submit(new SubmitInput());
      if (expectedExceptionType != null) {
        fail("Expected exception of type " + expectedExceptionType.getSimpleName());
      }
    } catch (RestApiException e) {
      if (expectedExceptionType == null) {
        throw e;
      }
      if (!expectedExceptionType.isAssignableFrom(e.getClass())) {
        // More verbose than assertThat, but gives stacktrace.
        throw new AssertionError(
            "Expected exception of type "
                + expectedExceptionType.getSimpleName()
                + "but got exception of type "
                + e.getClass().getSimpleName(),
            e);
      }
      assertThat(e.getMessage()).containsMatch(expectedExceptionMessagePattern);
      return;
    }
    ChangeInfo change = gApi.changes().id(changeId).info();
    assertThat(change.status).isEqualTo(ChangeStatus.MERGED);
  }
}

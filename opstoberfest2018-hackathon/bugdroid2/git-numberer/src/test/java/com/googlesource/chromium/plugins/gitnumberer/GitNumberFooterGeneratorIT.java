package com.googlesource.chromium.plugins.gitnumberer;

import static com.google.common.truth.Truth.assertThat;
import static com.google.gerrit.extensions.client.ListChangesOption.CURRENT_REVISION;

import com.google.gerrit.acceptance.PushOneCommit;
import com.google.gerrit.common.FooterConstants;
import com.google.gerrit.extensions.api.changes.SubmitInput;
import com.google.gerrit.extensions.api.projects.ProjectInput;
import com.google.gerrit.extensions.client.SubmitType;
import com.google.gerrit.extensions.restapi.ResourceConflictException;
import org.eclipse.jgit.lib.ObjectId;
import org.eclipse.jgit.revwalk.RevCommit;
import org.junit.Test;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class GitNumberFooterGeneratorIT extends LightweightWithConfigIT {
  private static final Logger log = LoggerFactory.getLogger(GitNumberFooterGeneratorIT.class);

  @Override
  protected void updateProjectInput(ProjectInput in) {
    in.submitType = SubmitType.REBASE_ALWAYS;
  }

  @Test
  public void mergeInvalidParentMissingFooterMisconfiguration() throws Exception {
    // This should NOT happen in production normally.
    configurePlugin(ConfigFor.VALIDATOR, "refs/not-heads/*");
    configurePlugin(ConfigFor.GENERATOR, "refs/heads/*");
    assertDisabledPlugin(ConfigFor.VALIDATOR, "refs/heads/master");
    assertEnabledPlugin(ConfigFor.GENERATOR, "refs/heads/master");

    PushOneCommit.Result change = createChange();
    change.assertOkStatus();
    assertThat(change.getCommit().getFooterLines(FooterConstants.REVIEWED_BY)).hasSize(0);
    approve(change.getChangeId());
    try {
      gApi.changes().id(change.getChangeId()).current().submit(new SubmitInput());
      assertThat("unrechable").isNotNull();
    } catch (ResourceConflictException e) {
      // TODO(tandrii): propagate exception to user.
      assertThat(e).isNotNull();
    }
  }

  @Test
  public void mergeInvalidParentMissingFooter() throws Exception {
    // This might happen in production: missing parent footer would mean that
    // validator rejects all commits on top of it.
    configurePlugin("refs/heads/*");
    assertEnabledPlugin("refs/heads/master");

    PushOneCommit.Result change = createChange();
    change.assertOkStatus();
    assertThat(change.getCommit().getFooterLines(FooterConstants.REVIEWED_BY)).hasSize(0);
    approve(change.getChangeId());
    try {
      gApi.changes().id(change.getChangeId()).current().submit(new SubmitInput());
      throw new IllegalStateException();
    } catch (ResourceConflictException e) {
      // Validator should reject the submit.
      // TODO(tandrii): the error message should clearly say that parent commit
      // is the problem. Unfortunately, it's not easy to do this without either
      // refactoring of validator OR "faking" valid-looking footer in Generator.
      assertThat(e.getMessage()).contains("Cr-Commit-Position footer is required");
    }
  }

  @Test
  public void mergeIntended() throws Exception {
    configurePlugin("refs/heads/not-master");
    assertDisabledPlugin("refs/heads/master");

    PushOneCommit.Result parent =
        createChange(
            "This is a dirty hack :) \n\n" + "Cr-Commit-Position: refs/heads/master@{#13}",
            "a.txt",
            "whatever");
    parent.assertOkStatus();
    approve(parent.getChangeId());
    gApi.changes().id(parent.getChangeId()).current().submit(new SubmitInput());
    testRepo = cloneProject(project);
    RevCommit r =
        testRepo
            .getRevWalk()
            .parseCommit(
                ObjectId.fromString(get(parent.getChangeId(), CURRENT_REVISION).currentRevision));
    assertThat(r.getFooterLines(FooterConstants.REVIEWED_ON)).hasSize(1);
    assertThat(r.getFooterLines("Cr-Commit-Position")).containsExactly("refs/heads/master@{#13}");

    configurePlugin("refs/heads/master");
    assertEnabledPlugin("refs/heads/master");
    // Now we can push child and its message should be auto-generated.
    log.info(
        "ready to create a good change on top of good {} with message\n{}\n",
        r.getName(),
        r.getFullMessage());
    PushOneCommit.Result change = createChange();
    assertThat(change.getCommit().getParent(0).getName()).isEqualTo(r.getName());
    change.assertOkStatus();
    approve(change.getChangeId());
    gApi.changes().id(change.getChangeId()).current().submit(new SubmitInput());

    testRepo.git().fetch().setRemote("origin").call();
    r =
        testRepo
            .getRevWalk()
            .parseCommit(
                ObjectId.fromString(get(change.getChangeId(), CURRENT_REVISION).currentRevision));
    assertThat(r.getFooterLines("Cr-Error")).hasSize(0);
    assertThat(r.getFooterLines("Cr-Commit-Position")).containsExactly("refs/heads/master@{#14}");
    assertThat(r.getFooterLines(FooterConstants.REVIEWED_ON)).hasSize(1);
    assertThat(r.getFooterLines(FooterConstants.REVIEWED_BY)).hasSize(1);
  }
}

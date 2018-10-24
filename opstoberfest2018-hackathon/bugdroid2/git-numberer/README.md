# Git Numberer Gerrit Plugin

This plugin ensures commit footers in a repository comply with rules of
[Git number footers for Chromium](
https://docs.google.com/document/d/1i0pNHKagCsGxOIT7H44kk2mnTEjV9BdfgBjVleFhBr0/edit?usp=sharing)
and is part of the [Git Numberer for Chromium](https://goto.google.com/git-numberer)
system.

## Summary

For every new **commit C** that is about to be pushed with `git push` or landed
using Gerrit API/UI (called *merged* in Gerrit), this plugin ensures:

1. **commit C** having exactly at most one parent, namely **commit P**.
2. **commit P** contains footer `Cr-Commit-Position: refs/foo/bar@{#X}`, where
   `X` is positive integer.
3. **commit C** contains footer `Cr-Commit-Position: refs/foo/bar@{#Y}` such
   that `Y = X+1`.

There is more to it in the doc [Git number footers for
Chromium](https://goto.google.com/git-numberer).

## Plugin structure

This plugin consists of verification and generation parts, each working
independently of each other, but share common libraries.
While each part can be enabled on specific refs independently of another,
it's recommended that verifier is enabled on all refs on which generation is
enabled.

### Verification

Safety comes first. This plugin installs a verifier that ensures that all new
commits on **enabled** refs comply with the numbering scheme. The new commits
may be created as a result of landing (merging) a Gerrit changelist, or as a
result of a git push operation.

**NOTE** This is a Gerrit plugin and thus it only works for operations done
through Gerrit. Thus, this plugin won't protect from bad commits being pushed by
someone with direct access to Git repository filesystem on Gerrit's server.
Google's deployment of Gerrit internally calls such access **_direct push**.
Such access could be useful to administrators when pushing humongous histories
as in during [Chromium + Blink
merge](https://www.chromium.org/blink/blink-post-merge-faq), but then
administrators are responsible for verification.

### Generation

TODO(Tandrii): implement and document.


### See also:

* `git cl` and its fork in [Commit Queue](
https://dev.chromium.org/developers/testing/commit-queue) which generate footers
for Rietveld issues.


## Development

### Get Ready, only once.

Follow this [general Gerrit guide
first](https://gerrit-review.googlesource.com/Documentation/#_developer) to get
basic set up correctly.

### Code/Build/Test

**NB** BUCK used with Gerrit no longer has symlinking issues as of September
2016. **TODO(tandrii):** consider reworking these instructions and making CI
      possible.

To avoid wasting hours with Buck's symlinking issues, I don't symlink the plugin
into `gerrit/plugins`, but instead add it as a submodule. I also add plugin
under development to `custom` list of `core` plugins, which integrates well with
existing gerrit tooling. See this
[CL](https://gerrit-review.googlesource.com/89684) for this integration.

These 3 vars are assumed to be set in instructions below:

    export GERRIT_SRC=<path to where you cloned gerrit repo>
    export PLUGIN=git-numberer
    # Optional. See general Gerrit developer guide above to learn more.
    export GERRIT_TEST=<path where you initialized and run gerrit locally>

Get plugin source to a hackable state:

    cd $GERRIT_SRC
    git new-branch do-not-commit-$PLUGIN
    git fetch https://gerrit.googlesource.com/gerrit refs/changes/84/89684/1
    git cherry-pick FETCH_HEAD
    git submit init
    git submodule update --recursive
    ./tools/eclipse/project.py  # For Eclipse users.
    cd plugins/$PLUGIN
    git new-branch hacking
    # Hack hack hack, commit, upload, etc.

Build plugin:

    cd $GERRIT_SRC && buck build //plugins/$PLUGIN:$PLUGIN

Optionally, make use of new version in your local Gerrit server:
    
    cp $GERRIT_SRC/buck-out/gen/plugins/$PLUGIN/$PLUGIN.jar \
                   $GERRIT_TEST/plugins/ && \
       $GERRIT_TEST/bin/gerrit.sh restart
    # You may want to keep watching log file in advance in case of errors.
    tail -F $GERRIT_TEST/logs/error_log

Test plugin:
    
    cd $GERRIT_SRC && buck test //plugins/$PLUGIN:$PLUGIN-test

You can also test directly from Eclipse if you ran
`$GERRIT_SRC/tools/eclipse/project.py` command.


## References

* [Git number footers for Chromium](https://docs.google.com/document/d/1i0pNHKagCsGxOIT7H44kk2mnTEjV9BdfgBjVleFhBr0/edit?usp=sharing)
* TODO(tandrii): make git-numberer a public doc in chromium.org domain: [Git number as
  Gerrit Plugins](https://goto.google.com/git-numberer)
* [Commit Queue](https://dev.chromium.org/developers/testing/commit-queue)

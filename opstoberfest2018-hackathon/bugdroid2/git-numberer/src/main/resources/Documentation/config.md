Configuration
=============

The configuration of the @PLUGIN@ plugin is done on project level in
the `project.config` file of the project.

Project owners can do the configuration in the Gerrit web UI from
project info screen.

```
  [plugin "@PLUGIN@"]
    validate-disabled-refglob = refs/heads/infra/config
    validate-enabled-refglob = refs/heads/master
    validate-enabled-refglob = refs/branch-heads/*
    # Generation *should* normally be enabled only on refs on
    # which validation is also enabled.
    generate-disabled-refglob = refs/heads/infra/config
    generate-enabled-refglob = refs/heads/master
    generate-enabled-refglob = refs/branch-heads/*
```

plugin.@PLUGIN@.validate-disabled-refglob
:	refs on which no verification will be done.

	validate-disabled-refglob(s) are *not* inherited by child projects.

plugin.@PLUGIN@.validate-enabled-refglob
:	refs on which verification will be done unless also matching validate-disabled-refglob.

	validate-enabled-refglob(s) are *not* inherited by child projects.

plugin.@PLUGIN@.generate-disabled-refglob
:	refs on which no generation will be done.

	generate-disabled-refglob(s) are *not* inherited by child projects.

plugin.@PLUGIN@.generate-enabled-refglob
:	refs on which generation will be done unless also matching generate-disabled-refglob.

	generate-enabled-refglob(s) are *not* inherited by child projects.


Plugin @PLUGIN@ validates commits on some ref **if and only if all conditions
below are met**:
 * ref is not a magic ref `refs/for/*`
 * ref is not used for Gerrit project config `refs/meta/config`
 * ref is not matched by any `validate-disabled-globs`
 * ref is matched by at least one `validate-enabled-globs`.

Thus, even if this plugin is misconfigured, developers can still upload new
changes and administrator can still fix the config.

The same applies for generation of commit footers on a specific ref, which is controlled
by `generate-enabled-globs` and `generate-disabled-globs`.

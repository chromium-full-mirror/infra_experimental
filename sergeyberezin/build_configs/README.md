# Chromium [and other clients] build(er) configs

This is an attempt to create a few samples of build configs that would work for
Chromium, and will be a lot easier to navigate and support by devs than the
current format.

We use Starlark for the config format. The scope is any builder / test configs
that are not for LUCI services. Specifically:

- mb_config.pyl
- testing/buildbot/*.pyl
- any master-specific configs recipe-side
- recipe's config.py configs

The experiment is less concerned with generation of the actual configs, and more
with the new format of the configs. Once the format is deemed acceptable, we can
implement the generation for it.

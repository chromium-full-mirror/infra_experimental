Chrome Infrastructure is responsible for repositories, code review, building
and testing of Chromium and related projects.

If you want to contribute to the Chromium browser, you're in the wrong
place. See http://dev.chromium.org/getting-involved instead.

If you cannot find what you're looking for here, take a look at our
[old wiki](http://dev.chromium.org/infra) and feel free to ask questions on
infra-dev@chromium.org.

Most of the documentation relates to
[infra.git](https://chromium.googlesource.com/infra/infra/) repository.

## General information

* [Source code](source.git)
* [Using the infra.git repository](usage.md): running commands and tools
* [Structure of the infra.git repositoryt](structure.md)
* [Deployment of infra.git Services](deployment.md)
* [Reference documentation](
  https://storage.googleapis.com/chromium-infra-docs/infra/html/reference/modules.html)
  , extracted from docstrings

## Usage Guides

* [How to set up a new buildbot master](user_guide/new_master.md)
* [Recipes user guide](user_guide/recipes.md)
* [The builders.pyl file format for masters](user_guide/builders_pyl.md).
* [Buildbot master authentication to Cloud Endpoints](master_auth.md)

## Contributer's Guides

* [Contributing to infra.git](contributing.md)
* [Documenting](documenting.md)
* [Testing](testing.md)
* [Logging](logging.md)
* [Flags](flags.md)
* [Appengine apps](appengine.md)

TBD:

* How to handle authentication
* How to add a new tool.

## Technical Background

This section explains some technical choices.

* [Dependency handling in infra.git](bootstrap.md). How it works and
  why it's structured this way.

## Other topics

* [list of infra steps on waterfall and tryserver](steps.md)

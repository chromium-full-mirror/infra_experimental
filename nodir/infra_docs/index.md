# Chrome Infra infra.git Repository

This documentation describes the new (as of March 2014) repository
containing the public code for the Chrome infrastructure: infra.git. The
old repository is called build/, and is based in SVN.

If you want to contribute to the Chromium browser, you're in the wrong
place. See
[<http://dev.chromium.org/getting-involved>](http://dev.chromium.org/getting-involved)
instead. You can find more information on the Chrome infrastructure
[here](http://dev.chromium.org/infra).

If you cannot find what you're looking for here, feel free to ask
questions on <infra-dev@chromium.org>.

## General Information

*  [installation](installation.md) - getting infra.git on your local
    workstation
*  [usage](usage.md) - running commands and tools
*  [structure](structure.md) - overview of the general repository
    layout
*  [deployment](deployment.md) - how tools and services are deployed
*  [contributing](contributing.md) - how to make changes to the
    repository
*  [reference/modules](reference/modules.md) - reference documentation,
    extracted from docstrings.

## Usage Guides

*  [user\_guide/new\_master](user\_guide/new\_master.md) - How to set
    up a new buildbot master.
*  [user\_guide/recipes](user\_guide/recipes.md) - Recipes user guide.
*  [user\_guide/builders\_pyl](user\_guide/builders\_pyl.md) - The
    builders.pyl file format for masters.
*  [master\_auth](master\_auth.md)

## Contributer's Guides

*  [documenting](documenting.md) - what and how to document, plus some
    technical information on the compilation/deployment pipeline.
*  [testing](testing.md) - tools used, how and why.
*  [logging](logging.md) - how logging works in infra.git.
*  [flags](flags.md) - how to process command-line arguments.
*  [appengine](appengine.md) - How to develop an appengine app in
    infra.git

TBD:

*  How to handle authentication
*  How to add a new tool - also gives example usage of
    [reference/infra.libs](reference/infra.libs.md)

## Technical Background

This section explains some technical choices.

*  [bootstrap](bootstrap.md) - Dependency handling. How it works and
    why it's structured this way.

## Other topics

*  [steps](steps.md) - list of infra steps on waterfall and tryserver


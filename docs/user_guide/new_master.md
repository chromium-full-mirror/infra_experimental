# Setting Up a New Master

To set up a new master, you need three ports. File an [Infra-Labs
ticket](https://code.google.com/p/chromium/issues/entry?labels=Type-Bug,Pri-2,Infra-Labs)
requesting ports for a new master and ask which VLAN your master should
be on (and hence which master\_base\_class you should use).

The port numbers and master\_base\_class settings go into your
`builders.pyl` config file (see below).

Then create a new master directory in `build/masters` or
`build_internal/masters` depending on whether this is a Google internal
master.:

    $ cd $BUILD_DIR/masters
    $ mkdir master.foo.bar
    $ cd master.foo.bar

Create a `builders.pyl` file describing the builders on this master. The
format is documented in [the builders.pyl file format
\<builders\_pyl\>](the builders.pyl file format \<builders\_pyl\>.md)\_.
Set the port numbers and master\_base\_class to the values you got from
Labs, above.

You will also need slaves allocated for all your builders. File an
[Infra-Labs
ticket](https://code.google.com/p/chromium/issues/entry?labels=Type-Bug,Pri-2,Infra-Labs)
for those also, and specify how many of each configuration you will
need. They will be configured in this file.:

    $ cp $BUILD_DIR/masters/master.chromium.mojo/builders.pyl .
    <edit builders.pyl to taste>

After this file exists, you can use `buildbot-tool` to generate the rest
of the master configuration.:

    $ $BUILD_DIR/scripts/tools/buildbot-tool gen `pwd`

You'll also need to add your new master to the long list in
`$BUILD_DIR/tests/masters_test.py`.:

    # Add this line to $BUILD_DIR/tests/masters_test.py next to the other lines
    # that look like this.
    'master.foo.bar': 'FooBar',

You can find the class name `FooBar` in the `master_site_config.py` that
was generated in your master directory.

Commit what you have, then file a third, final [Infra-Labs
ticket](https://code.google.com/p/chromium/issues/entry?labels=Type-Bug,Pri-2,Infra-Labs)
asking for the appropriate URLs to be set up for your master.

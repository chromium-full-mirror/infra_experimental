load("//tools/bzl:junit.bzl", "junit_tests")
load("//tools/bzl:plugin.bzl", "gerrit_plugin", "PLUGIN_DEPS", "PLUGIN_TEST_DEPS")

gerrit_plugin(
    name = "git-numberer",
    srcs = glob(["src/main/java/**/*.java"]),
    manifest_entries = [
        "Gerrit-PluginName: git-numberer",
        "Implementation-Title: Git Numberer plugin",
        "Gerrit-Module: com.googlesource.chromium.plugins.gitnumberer.GitNumbererModule",
    ],
    resources = glob(["src/main/resources/**/*"]),
)

junit_tests(
    name = "git_numberer_tests",
    srcs = glob(["src/test/java/**/*.java"]),
    tags = ["git-numberer"],
    deps = PLUGIN_DEPS + PLUGIN_TEST_DEPS + [
        ":git-numberer__plugin",
    ],
)

// Copyright 2016 The Chromium Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

package com.googlesource.chromium.plugins.gitnumberer;

import static com.google.common.truth.Truth.assertThat;

import com.google.gerrit.server.config.PluginConfig;
import java.util.Arrays;
import java.util.List;
import org.eclipse.jgit.lib.Config;
import org.junit.Test;

public class ConfigTest {

  @Test
  public void validGlob() {
    assertThat(RefGlobMatcher.isValidGlob("*")).isTrue();
    assertThat(RefGlobMatcher.isValidGlob("refs/a/*")).isTrue();
    assertThat(RefGlobMatcher.isValidGlob("refs/a/*.*")).isTrue();
    assertThat(RefGlobMatcher.isValidGlob("*-refs/a/*.*")).isTrue();
  }

  @Test
  public void invalidGlob() {
    assertThat(RefGlobMatcher.isValidGlob("?")).isFalse();
    assertThat(RefGlobMatcher.isValidGlob("refs\\")).isFalse();
    assertThat(RefGlobMatcher.isValidGlob("refs+")).isFalse();
    assertThat(RefGlobMatcher.isValidGlob("refs/master/{}")).isFalse();
    assertThat(RefGlobMatcher.isValidGlob("refs/whatever/()")).isFalse();
  }

  @Test
  public void translate() {
    assertThat(RefGlobMatcher.translate("refs/heads")).isEqualTo("refs/heads");
    assertThat(RefGlobMatcher.translate("refs/*")).isEqualTo("refs/.*");
    assertThat(RefGlobMatcher.translate("refs/*.*")).isEqualTo("refs/.*\\..*");
  }

  @Test
  public void match() {
    String[] globs =
        new String[] {"refs/heads/master", "refs/heads/infra/*", "refs/branch-heads/*.*.*"};
    assertThat(RefGlobMatcher.matches("refs/heads/master", globs)).isTrue();
    assertThat(RefGlobMatcher.matches("refs/heads/infra/config", globs)).isTrue();
    assertThat(RefGlobMatcher.matches("refs/branch-heads/1.2.3", globs)).isTrue();
    assertThat(RefGlobMatcher.matches("refs/branch-heads/1.2.3.a", globs)).isTrue();

    assertThat(RefGlobMatcher.matches("refs/heads/other", globs)).isFalse();
    assertThat(RefGlobMatcher.matches("refs/heads/infra", globs)).isFalse();
    assertThat(RefGlobMatcher.matches("refs/branch-heads/nodots", globs)).isFalse();
    assertThat(RefGlobMatcher.matches("refs/branch-heads/no.s", globs)).isFalse();
  }

  @Test
  public void disabledByDefault() {
    PluginConfig cfg = createConfig(Arrays.asList(), Arrays.asList());
    assertDisabled("refs/bla", cfg);
    assertDisabled("refs/bla", cfg);
    assertDisabled("anything", cfg);

    assertDisabled("refs/meta/config", cfg);
    assertDisabled("refs/for/anything", cfg);
  }

  @Test
  public void disabledTakesPrecedence() {
    PluginConfig cfg =
        createConfig(Arrays.asList("refs/heads/disabled"), Arrays.asList("refs/heads/*"));
    assertDisabled("refs/heads/disabled", cfg);
    assertEnabled("refs/heads/master", cfg);

    assertDisabled("still-disabled", cfg);

    assertDisabled("refs/meta/config", cfg);
    assertDisabled("refs/for/anything", cfg);
  }

  @Test
  public void withRegexes() {
    PluginConfig cfg = createConfig(Arrays.asList("experimental-*"), Arrays.asList("*.*"));
    assertDisabled("unmatching", cfg);
    assertDisabled("experimental-anything", cfg);
    assertEnabled("this.enabled", cfg);

    assertDisabled("still-disabled", cfg);

    assertDisabled("refs/meta/config", cfg);
    assertDisabled("refs/for/anything", cfg);
  }

  @Test
  public void differentConfigs() {
    PluginConfig cfg =
        createConfig(Arrays.asList("refs/heads/disabled"), Arrays.asList("refs/heads/*"));
    cfg.setStringList(ConfigFields.GENERATE_ENABLED, Arrays.asList("refs/heads/*.*"));
    cfg.setStringList(ConfigFields.GENERATE_DISABLED, Arrays.asList("refs/heads/1.1"));
    assertDisabled("refs/other/head", cfg);
    assertEnabled("refs/heads/mas.ter", cfg);

    assertThat(CommitValidator.isEnabled("refs/heads/master", cfg)).isTrue();
    assertThat(Generator.isEnabled("refs/heads/master", cfg)).isFalse();

    assertThat(CommitValidator.isEnabled("refs/heads/1.1", cfg)).isTrue();
    assertThat(Generator.isEnabled("refs/heads/1.1", cfg)).isFalse();
  }

  private void assertEnabled(String ref, PluginConfig cfg) {
    assertThat(CommitValidator.isEnabled(ref, cfg)).isTrue();
    assertThat(Generator.isEnabled(ref, cfg)).isTrue();
  }

  private void assertDisabled(String ref, PluginConfig cfg) {
    assertThat(CommitValidator.isEnabled(ref, cfg)).isFalse();
    assertThat(Generator.isEnabled(ref, cfg)).isFalse();
  }

  private PluginConfig createConfig(List<String> disabled, List<String> enabled) {
    Config projectConfig = new Config();
    projectConfig.setStringList("plugin", "test", ConfigFields.VALIDATE_DISABLED, disabled);
    projectConfig.setStringList("plugin", "test", ConfigFields.GENERATE_DISABLED, disabled);
    projectConfig.setStringList("plugin", "test", ConfigFields.VALIDATE_ENABLED, enabled);
    projectConfig.setStringList("plugin", "test", ConfigFields.GENERATE_ENABLED, enabled);
    return new PluginConfig("test", projectConfig);
  }
}

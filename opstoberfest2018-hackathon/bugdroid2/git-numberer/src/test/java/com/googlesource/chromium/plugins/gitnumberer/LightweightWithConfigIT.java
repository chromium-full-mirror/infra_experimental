// Copyright 2017 The Chromium Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

package com.googlesource.chromium.plugins.gitnumberer;

import static com.google.common.truth.Truth.assertThat;

import com.google.gerrit.acceptance.LightweightPluginDaemonTest;
import com.google.gerrit.acceptance.TestPlugin;
import com.google.gerrit.server.config.PluginConfig;
import com.google.gerrit.server.git.meta.MetaDataUpdate;
import com.google.gerrit.server.project.ProjectConfig;
import com.google.gerrit.server.project.NoSuchProjectException;
import com.google.inject.Inject;
import java.io.IOException;
import java.util.Arrays;
import java.util.List;
import org.eclipse.jgit.errors.ConfigInvalidException;
import org.junit.Test;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

@TestPlugin(
  name = "git-numberer",
  sysModule = "com.googlesource.chromium.plugins.gitnumberer.GitNumbererModule"
)
public class LightweightWithConfigIT extends LightweightPluginDaemonTest {
  protected static String pluginName = "git-numberer";
  private static final Logger log = LoggerFactory.getLogger(LightweightWithConfigIT.class);

  @Inject private com.google.gerrit.server.config.PluginConfigFactory pluginCfgFactory;

  enum ConfigFor {
    SYMMETRIC,
    GENERATOR,
    VALIDATOR;
  }

  @Test
  public void testConfigSetup() throws Exception {
    String ref = "refs/heads/some";
    configurePlugin(ref, ref + "_suffix");
    assertEnabledPlugin(ref);
    assertEnabledPlugin(ref + "_suffix");

    disablePlugin();
    assertDisabledPlugin(ref);

    configurePlugin(ConfigFor.GENERATOR, ref);
    assertEnabledPlugin(ConfigFor.GENERATOR, ref);
    assertDisabledPlugin(ConfigFor.VALIDATOR, ref);
  }

  protected void disablePlugin() throws IOException, ConfigInvalidException {
    configurePlugin(Arrays.asList(), Arrays.asList(), ConfigFor.SYMMETRIC);
  }

  protected void configurePlugin() throws IOException, ConfigInvalidException {
    configurePlugin(
        Arrays.asList("refs/heads/*", "refs/releases/*.*"),
        Arrays.asList("refs/heads/disabled", "refs/heads/infra/config"),
        ConfigFor.SYMMETRIC);
  }

  protected void configurePlugin(ConfigFor configFor, String... params)
      throws IOException, ConfigInvalidException {
    configurePlugin(
        Arrays.asList(params),
        Arrays.asList("refs/heads/disabled", "refs/heads/infra/config"),
        configFor);
  }

  protected void configurePlugin(String... params) throws IOException, ConfigInvalidException {
    configurePlugin(
        Arrays.asList(params),
        Arrays.asList("refs/heads/disabled", "refs/heads/infra/config"),
        ConfigFor.SYMMETRIC);
  }

  protected void configurePlugin(List<String> enabled, List<String> disabled, ConfigFor configFor)
      throws IOException, ConfigInvalidException {
    /*
     * super().pluginName is set based on super reliable parsing of BUCK file.
     * So, if it seems that config isn't being set/read properly, make sure this
     * test and plugin implementation actually agree on name of the plugin.
     */

    // WARNING: if you ever need to change the next assertion,
    // be ABSOLUTELY SURE that you are ready to lose all existing configs on
    // deployment.
    assertThat(pluginName).isEqualTo("git-numberer");

    try (MetaDataUpdate md = metaDataUpdateFactory.create(project)) {
      md.setMessage(String.format("Change plugin permission"));
      ProjectConfig projectConfig = ProjectConfig.read(md);
      PluginConfig pluginConfig = projectConfig.getPluginConfig(pluginName);

      if (configFor != ConfigFor.GENERATOR) {
        pluginConfig.setStringList(ConfigFields.VALIDATE_ENABLED, enabled);
        pluginConfig.setStringList(ConfigFields.VALIDATE_DISABLED, disabled);
      }
      if (configFor != ConfigFor.VALIDATOR) {
        pluginConfig.setStringList(ConfigFields.GENERATE_ENABLED, enabled);
        pluginConfig.setStringList(ConfigFields.GENERATE_DISABLED, disabled);
      }
      projectConfig.commit(md);
      projectCache.evict(project);
    }
    log.info(
        "configured plugin {} on {} excluding {} for {}", pluginName, enabled, disabled, configFor);
  }

  protected void assertEnabledPlugin(String ref) throws NoSuchProjectException {
    assertEnabledPlugin(ConfigFor.SYMMETRIC, ref);
  }

  protected void assertEnabledPlugin(ConfigFor configFor, String ref)
      throws NoSuchProjectException {
    assertThat(ref).startsWith("refs");
    PluginConfig cf = pluginCfgFactory.getFromProjectConfig(project, pluginName);
    if (configFor != ConfigFor.GENERATOR) {
      assertThat(CommitValidator.isEnabled(ref, cf))
          .named(
              "ref: %s enabled: %s disabled: %s",
              ref,
              cf.getStringList(ConfigFields.VALIDATE_ENABLED),
              cf.getStringList(ConfigFields.VALIDATE_DISABLED))
          .isTrue();
    }
    if (configFor != ConfigFor.VALIDATOR) {
      assertThat(Generator.isEnabled(ref, cf))
          .named(
              "ref: %s enabled: %s disabled: %s",
              ref,
              cf.getStringList(ConfigFields.GENERATE_ENABLED),
              cf.getStringList(ConfigFields.GENERATE_DISABLED))
          .isTrue();
    }
  }

  protected void assertDisabledPlugin(String ref) throws NoSuchProjectException {
    assertDisabledPlugin(ConfigFor.SYMMETRIC, ref);
  }

  protected void assertDisabledPlugin(ConfigFor configFor, String ref)
      throws NoSuchProjectException {
    assertThat(ref).startsWith("refs");
    PluginConfig cf = pluginCfgFactory.getFromProjectConfig(project, pluginName);
    if (configFor != ConfigFor.GENERATOR) {
      assertThat(CommitValidator.isEnabled(ref, cf))
          .named(
              "ref: %s enabled: %s disabled: %s",
              ref,
              cf.getStringList(ConfigFields.VALIDATE_ENABLED),
              cf.getStringList(ConfigFields.VALIDATE_DISABLED))
          .isFalse();
    }
    if (configFor != ConfigFor.VALIDATOR) {
      assertThat(Generator.isEnabled(ref, cf))
          .named(
              "ref: %s enabled: %s disabled: %s",
              ref,
              cf.getStringList(ConfigFields.GENERATE_ENABLED),
              cf.getStringList(ConfigFields.GENERATE_DISABLED))
          .isFalse();
    }
  }
}

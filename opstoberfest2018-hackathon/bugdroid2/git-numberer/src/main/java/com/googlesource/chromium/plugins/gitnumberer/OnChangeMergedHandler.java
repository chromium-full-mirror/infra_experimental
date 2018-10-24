// Copyright 2017 The Chromium Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

package com.googlesource.chromium.plugins.gitnumberer;

import com.google.gerrit.server.events.Event;
import com.google.gerrit.server.events.EventListener;
import com.google.gerrit.server.events.ChangeMergedEvent;

public class OnChangeMergedHandler implements EventListener {
  @Override
  public void onEvent(Event event) {
    if (event instanceof ChangeMergedEvent) {
      ChangeMergedEvent convertedEvent = (ChangeMergedEvent) event;
    }
  }
}

// Copyright (C) 2016 The Android Open Source Project
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
// http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

(function(i,s,o,g,r,a,m){i['GoogleAnalyticsObject']=r;i[r]=i[r]||function(){
(i[r].q=i[r].q||[]).push(arguments)},i[r].l=1*new Date();a=s.createElement(o),
m=s.getElementsByTagName(o)[0];a.async=1;a.src=g;m.parentNode.insertBefore(a,m)
})(window,document,'script','https://www.google-analytics.com/analytics.js',
'ga');

ga('create', 'UA-XXXXXXX-1', {
  'siteSpeedSampleRate': 100,
  'cookieDomain': 'none',
});
ga('set', 'checkProtocolTask', null);
ga('send', 'pageview');

var RequestType = {
  NAV: 'nav-report',
  TIMING: 'timing-report',
};

chrome.runtime.onMessage.addListener(function(request) {
  var detail = request.detail;
  var version = detail.ver || chrome.app.getDetails().version;

  ga('set', 'dimension1', version);
  ga('set', 'dimension2', detail.host);

  switch (request.type) {
    case RequestType.TIMING:
      var time = Math.round(detail.value);
      var hourInMillis = 1000 * 60 * 60;
      if (0 < time && time < hourInMillis) {
        ga('send', 'timing', detail.category, detail.name, time);
      } else {
        console.log(
          'timing out of range: ' + [detail.category, detail.name, time]);
      }
      break;
    case RequestType.NAV:
      ga('set', 'page', detail.value);
      ga('send', 'pageview');
      break;
  };
});

function loadImage(path, width, height) {
  return new Promise(function(resolve) {
    var canvas = document.createElement('canvas');
    var ctx = canvas.getContext('2d');
    var image = new Image();
    var imageData;
    image.onload = function() {
      ctx.drawImage(image, 0, 0, width, height);
      imageData = ctx.getImageData(0, 0, width, height);
      resolve(imageData);
    };
    image.src = chrome.runtime.getURL(path);
  });
}

chrome.runtime.onInstalled.addListener(function() {
  var loadImages = Promise.all([
    loadImage('icon_active_32.png', 32, 32),
    loadImage('icon_active_192.png', 192, 192),
  ]);

  loadImages.then(function(imageDataArray) {
    chrome.declarativeContent.onPageChanged.removeRules(undefined, function() {
      chrome.declarativeContent.onPageChanged.addRules([
        {
          conditions: [
            new chrome.declarativeContent.PageStateMatcher({
              pageUrl: { hostEquals: 'build.chromium.org' },
            }),
            new chrome.declarativeContent.PageStateMatcher({
              pageUrl: { hostEquals: 'ci.chromium.org' },
            }),
            new chrome.declarativeContent.PageStateMatcher({
              pageUrl: { hostEquals: 'uberchromegw.corp.google.com' },
            }),
          ],
          // And shows the extension's page action.
          actions: [ new chrome.declarativeContent.ShowPageAction() ]
        },
        {
          conditions: [
            new chrome.declarativeContent.PageStateMatcher({
              pageUrl: { hostEquals: 'ci.chromium.org' },
            })
          ],
          actions: [ new chrome.declarativeContent.SetIcon({
            imageData: {
              32: imageDataArray[0],
              192: imageDataArray[1],
            }
          })]
        }
      ]);
    });
  });
});

var WEB_REQUEST_FILTER_URLS = {
  urls: [
    "*://build.chromium.org/*",
    "*://ci.chromium.org/*",
    "*://uberchromegw.corp.google.com/i/*"
  ]
};

// There is no option to update a tab URL while also bypassing the cache. Hack
// around this limitation by setting a tab ID to be reloaded in the tab update
// callback below.
var tabIDToReload = null;
chrome.webRequest.onCompleted.addListener(
  function(details) {
    if (details.type === 'main_frame' && tabIDToReload != null) {
      chrome.tabs.reload(tabIDToReload, {bypassCache: true});
      tabIDToReload = null;
    }
  },
  WEB_REQUEST_FILTER_URLS
);

const BUILDBOT_URL = 'https://build.chromium.org/';
const MILO_URL = 'https://ci.chromium.org/';
const LOGIN_URL = MILO_URL + "auth/openid/login";

function redirectToBB(url) {
  if (url.hostname == "build.chromium.org" || url.hostname == "uberchromegw.corp.google.com") {
    return url.toString();
  }

  // Throw out the empty string at the beginning, since it always starts with a
  // slash
  let bySlash = url.pathname.split('/').slice(1);
  if (bySlash[0] != "buildbot") {
    return url.toString();
  }
  bySlash = bySlash.slice(1);
  if (bySlash[bySlash.length-1] == "") {
    bySlash = bySlash.splice(0, bySlash.length-1);
  }

  let pathname = "";
  if (bySlash.length == 2) {
    pathname = "p/" + bySlash[0] + "/builders/" + bySlash[1];
  } else if (bySlash.length == 3) {
    pathname = "p/" + bySlash[0] + "/builders/" + bySlash[1] + "/builds/" + bySlash[2];
  } else {
    return url.toString();
  }
  console.log("pathname", pathname, "for", bySlash);
  return BUILDBOT_URL + pathname;
}

function redirectToMilo(url) {
  if (url.hostname == "ci.chromium.org") {
    return url.toString();
  }

  // Throw out the empty string at the beginning, since it always starts with a
  // slash
  let bySlash = url.pathname.split('/').slice(1);
  if (bySlash[bySlash.length-1] == "") {
    bySlash = bySlash.splice(0, bySlash.length-1);
  }

  let pathname = "";
  if (bySlash.length >= 4 && (bySlash[0] == "p" || bySlash[0] == "i")) {
    if (bySlash.length == 4 && bySlash[2] == "builders") {
      pathname = bySlash[1] + "/" + bySlash[3];
    } else if (bySlash.length == 6 &&  bySlash[2] == "builders" && bySlash[4] == "builds") {
      pathname = bySlash[1] + "/" + bySlash[3] + "/" + bySlash[5];
    } else {
      // milo can't render this, just give up and go to BB
      return url.toString();
    }
  } else {
    return url.toString();
  }

  return MILO_URL + 'buildbot/' + pathname;
}

var enabled = false;
var cookieID = {
  name: 'BUILDBOT_UI',
  url: "https://build.chromium.org/",
};

chrome.cookies.get(cookieID, function(cookie) {
  if (cookie && cookie.value == "milo") {
    enabled = true;
  } else {
    enabled = false;
  }
});

chrome.webRequest.onBeforeRequest.addListener(
  function(details) {
    if (details.type !== 'main_frame') { return {}; }

    var url = new URL(details.url);
    let urlStr = '';
    if (enabled) {
      if (url.hostname != "ci.chromium.org") {
        urlStr = redirectToMilo(url);
      }
    }

    if (urlStr != details.url && urlStr != '') {
      return {
        redirectUrl: urlStr,
      };
    }

    return {};
  },
  WEB_REQUEST_FILTER_URLS,
  ['blocking']
);

chrome.pageAction.onClicked.addListener(function(tab) {
  chrome.cookies.get(cookieID, function(cookie) {
    if (cookie) {
      // We are on milo; switch to buildbot.
      chrome.cookies.remove(cookieID);
      enabled = false;
      chrome.tabs.update(tab.id, {
        url: redirectToBB(new URL(tab.url)),
      }, function(tab) {
        tabIDToReload = tab.id;
      });
      //ga('send', 'event', 'Page Action', 'Switch to Gerrit');
    } else {
      // We are on buildbot; switch to milo.
      console.log("setting enabled true");
      enabled = true;
      let url = redirectToMilo(new URL(tab.url));
      chrome.cookies.set({
        name: 'BUILDBOT_UI',
        value: 'milo',
        httpOnly: true,
        url: 'https://build.chromium.org/',
        secure: true,
      }, function() {
        chrome.tabs.update(tab.id, {
          url: url,
        }, function(tab) {
          chrome.tabs.reload(tab.id, {bypassCache: true});
        });
      });
    }
  });
});

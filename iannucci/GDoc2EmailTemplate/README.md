# GDoc2EmailTemplate

## What is this?

This is a Google AppsScript library which parses a Google Doc which
has been interlaced with scriptlet statements (as defined by [HtmlTemplate][]),
and returns a GMail-compatible HtmlTemplate for the body and document title as
the subject.

## How do I use it?

The library is available from the transpiled sources in this directory (using
`clasp push`) as Script ID:

    1UpB4cswTafGpFMQ0mI83EPNviVrtSSvS_1dc02aWh1q1GlL29LNJCpJy

You can include this as a library in e.g. a Google sheets application and
point it at the doc of your choosing to create a mail merge template. Once the
library has been added (lets assume you add it with the name GDoc2EmailTemplate),
you'd use it like:

    let parsed = GDoc2EmailTemplate.ParseDoc(<some DocumentApp.Document>)
    // mix in any context objects you want for the scriptlets to have access
    // to.
    parsed.body.myContextObject = {...}
    parsed.subject.myContextObject = {...}

    GmailApp.createDraft(
      "someuser@example.com",
      parsed.subject.evaluate().getContent(),
      "",
      {
        htmlBody: parsed.body.evaluate().getContent(),
        inlineImages: parsed.images
      }
    )

You can see the structure of the return value of ParseDoc. Unfortunately
Google Apps Script's current editor isn't smart enough to see it :(.

## Hacking

Mostly this revolves around getting `clasp` set up correctly... I'm not
_entirely_ sure what I did to get it working, but it involved some combination
of:

  * run `make init` to get all the node stuff
  * Enabling the "[Apps Script API][]"
  * running `npx clasp login` and completing the browser flow to make a
    'global' login.
  * minting an OAuth 2.0 client id from the [credentials ui][]
    * (+ Create Credentials > OAuth Client ID)
      * Application type == Desktop app
      * Name == whatever you want
    * Download the credential JSON to ~
    * run `npx clasp login --creds ~/.your_creds_file.json`

Once you have clasp running, you should be able to do `make push`,
`make test` and `make logs`.

I also highly recommend setting up e.g. nvim+YouCompleteMe or some other
IDE for type completion.

Another handy bit is running `npx tsc -w --noEmit` in another console
to continuously display any errors the compiler can detect.

[Apps Script API]: https://console.cloud.google.com/marketplace/product/google/script.googleapis.com?project=iannucci-personal
[credentials ui]: https://console.cloud.google.com/apis/credentials?project=iannucci-personal
[HtmlTemplate]: https://developers.google.com/apps-script/reference/html/html-template

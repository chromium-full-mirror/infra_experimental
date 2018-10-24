// Copyright 2017 The LUCI Authors. All rights reserved.
// Use of this source code is governed under the Apache License, Version 2.0
// that can be found in the LICENSE file.

package main

import (
	"bufio"
	"bytes"
	"flag"
	"fmt"
	"net/http"
	"os"

	"go.chromium.org/luci/auth"
	"go.chromium.org/luci/hardcoded/chromeinfra"

	"github.com/andygrunwald/go-gerrit"
	"github.com/google/skia-buildbot/go/gitiles"
)

func printUsage() {
	fmt.Printf("Usage: %s [OPTIONS] file-to-edit\n", os.Args[0])
	flag.PrintDefaults()
}

func getFullRepoUrl(repoFlag string) string {
	return repoFlag
}

func printErr(err error) {
	if err != nil {
		fmt.Println(err)
		os.Exit(1)
	}
}

func main() {
	authDefaults := chromeinfra.DefaultAuthOptions()

	authDefaults.Scopes = []string{
		auth.OAuthScopeEmail,
		"https://www.googleapis.com/auth/gerritcodereview",
	}

	repoFlag := flag.String("repo", "chromium/src", "Repo to change. Accepted formals are 'https://chromium.googlesource.com/chromium/src' or 'chromium/src'.")
	branchFlag := flag.String("branch", "master", "Branch to change.")
	issueNumFlag := flag.Int("issue-num", 0, "Existing issue to upload change to. Creates a new issue when not specified.")
	flag.Usage = printUsage
	flag.Parse()

	if flag.NArg() != 1 {
		flag.Usage()
		os.Exit(1)
	}
	fileName := flag.Arg(0)

	fmt.Printf("%s %s %d, %s\n\n", *repoFlag, *branchFlag, *issueNumFlag, fileName)

	instance := "https://chromium-review.googlesource.com/"
	client, err := gerrit.NewClient(instance, nil)
	printErr(err)
	// TODO: Read this from file.
	client.Authentication.SetCookieAuth("o", nil)

	repoClient := &http.Client{}
	repo := gitiles.NewRepo("https://chromium.googlesource.com/chromium/src", "/usr/local/google/home/bpastene/.gitcookies", repoClient)
	buff := bytes.Buffer{}
	writer := bufio.NewWriter(&buff)
	fmt.Printf("reading file from gitiles...\n")
	err = repo.ReadFileAtRef(fileName, *branchFlag, writer)
	printErr(err)
	fmt.Printf("got file\n\n")
	buff.WriteString("\ndid this work?\n")
	contents := buff.String()

	change := gerrit.ChangeInfo{}
	change.Project = "chromium/src"
	change.Branch = *branchFlag
	change.Subject = "test change; pls ignore"
	change.Status = "DRAFT"

	fmt.Printf("creating change...\n")
	newCh, resp, err := client.Changes.CreateChange(&change)
	printErr(err)
	fmt.Printf("resp status: %d, status: %s\n\n", resp.StatusCode, resp.Status)
	fmt.Printf("new id: %s\n", newCh.ID)

	fmt.Printf("creating edit...\n")
	resp, err = client.Changes.ChangeFileContentInChangeEdit(newCh.ID, fileName, contents)
	printErr(err)
	fmt.Printf("resp status: %d, status: %s\n\n", resp.StatusCode, resp.Status)

	fmt.Printf("publishing edit...\n")
	resp, err = client.Changes.PublishChangeEdit(newCh.ID, "")
	printErr(err)
	fmt.Printf("resp status: %d, status: %s\n\n", resp.StatusCode, resp.Status)

	os.Exit(0)
}

// Copyright 2017 The LUCI Authors. All rights reserved.
// Use of this source code is governed under the Apache License, Version 2.0
// that can be found in the LICENSE file.

package main

import (
	"bufio"
	"flag"
	"fmt"
	"io/ioutil"
	"net/http"
	"os"
	"os/exec"
	"os/user"
	"path"
	"strings"
	"time"

	"github.com/andygrunwald/go-gerrit"
	"github.com/google/skia-buildbot/go/gitiles"
)

func printUsage() {
	fmt.Printf("Usage: %s [OPTIONS] file-to-edit\n", os.Args[0])
	flag.PrintDefaults()
}

func getGerritUrl() string {
	// TODO: Make this configurable?
	return "https://chromium-review.googlesource.com/"
}

func getFullRepoUrl(repo string) string {
	// TODO: Make this configurable?
	baseGitilesUrl := "https://chromium.googlesource.com"
	return fmt.Sprintf("%s/%s", baseGitilesUrl, repo)
}

// Borrowed from https://skia.googlesource.com/buildbot/+/master/go/gitauth/gitauth.go
func getCredentials(gitCookiesPath string) (string, error) {
	dat, err := ioutil.ReadFile(gitCookiesPath)
	if err != nil {
		return "", err
	}
	contents := string(dat)
	for _, line := range strings.Split(contents, "\n") {
		if strings.HasPrefix(line, "#") || line == "" {
			continue
		}
		tokens := strings.Split(line, "\t")
		domain, xpath, key, value := tokens[0], tokens[2], tokens[5], tokens[6]
		if domain == ".googlesource.com" && xpath == "/" && key == "o" {
			return value, nil
		}
	}
	return "", fmt.Errorf("Git auth secret not found. Is there an entry for '.googlesource.com' in your gitcookies file?")
}

func doMain() error {
	// Get default location for gitcookies file.
	usr, err := user.Current()
	if err != nil {
		return err
	}
	homeDir := usr.HomeDir
	defGitCookiesFile := path.Join(homeDir, ".gitcookies")

	// Arg stuff.
	repoFlag := flag.String("repo", "chromium/src", "Repo to change, eg: 'chromium/src'.")
	branchFlag := flag.String("branch", "master", "Branch to change.")
	//TODO: Support this.
	//issueNumFlag := flag.Int("issue-num", 0, "Existing issue to upload change to. Creates a new issue when not specified.")
	gitCookiesPathFlag := flag.String("git-cookies-path", defGitCookiesFile, "Path to git cookies file to use for gerrit/gitiles auth.")
	flag.Usage = printUsage
	flag.Parse()
	if flag.NArg() != 1 {
		flag.Usage()
		return fmt.Errorf("Incorrect usage.")
	} else if _, err := os.Stat(*gitCookiesPathFlag); os.IsNotExist(err) {
		return fmt.Errorf("Git cookies file %s does not exist.\n", *gitCookiesPathFlag)
	}
	fileName := flag.Arg(0)

	// Pull the token from the gitcookie file.
	cookie, err := getCredentials(*gitCookiesPathFlag)
	if err != nil {
		return err
	}

	// Create a client for use with gitiles' API.
	fullRepoUrl := getFullRepoUrl(*repoFlag)
	client, err := gerrit.NewClient(getGerritUrl(), nil)
	if err != nil {
		return err
	}
	client.Authentication.SetCookieAuth("o", cookie)

	// Create a temp dir to store all our temp files.
	tmpDir, err := ioutil.TempDir("", "gerredit")
	if err != nil {
		return err
	}
	defer os.RemoveAll(tmpDir)

	// Fetch the contents of the file to edit from gitiles and place it in a temp file.
	tmpFile := path.Join(tmpDir, fileName)
	tmpFd, err := os.Create(tmpFile)
	if err != nil {
		return err
	}
	writer := bufio.NewWriter(tmpFd)
	repoClient := &http.Client{}
	repo := gitiles.NewRepo(fullRepoUrl, *gitCookiesPathFlag, repoClient)
	if err = repo.ReadFileAtRef(fileName, *branchFlag, writer); err != nil {
		fmt.Printf("error: %s, %s, %s\n", fullRepoUrl, fileName, *branchFlag)
		return err
	}
	writer.Flush()

	// Open the temp file in vim, then fetch its new contents.
	cmd := exec.Command("vim", tmpFile)
	cmd.Stdin = os.Stdin
	cmd.Stdout = os.Stdout
	if err = cmd.Run(); err != nil {
		return err
	}
	newFileContentsBytes, err := ioutil.ReadFile(tmpFile)
	if err != nil {
		return err
	}
	newFileContents := string(newFileContentsBytes[:])

	// Create a temp file to hold the commit message, and add a template.
	commitMsgHeader := `# Enter a description of the change.
# This will be displayed on the codereview site.
# The first line will also be used as the subject of the review.
#--------------------This line is 72 characters long--------------------
`
	commitMsgFooter := `
Bug:`
	tmpCommitMsgFile := path.Join(tmpDir, "commit_msg.txt")
	f, err := os.Create(tmpCommitMsgFile)
	if err != nil {
		return err
	}
	f.WriteString(commitMsgHeader)
	f.WriteString(commitMsgFooter)
	f.Sync()
	f.Close()

	// Open the commit message file in vim so the user can change it.
	cmd = exec.Command("vim", tmpCommitMsgFile)
	cmd.Stdin = os.Stdin
	cmd.Stdout = os.Stdout
	if err = cmd.Run(); err != nil {
		return err
	}

	// Read the commit msg, remove the header comments, and get the first line.
	commitMsgBytes, err := ioutil.ReadFile(tmpCommitMsgFile)
	if err != nil {
		return err
	}
	commitMsg := string(commitMsgBytes[:])
	commitMsg = strings.TrimSpace(commitMsg)
	// Chop off the first 3 lines.
	// TODO: Be smarter about what text to ignore (ie: the user might manually delete the first 3 lines).
	commitMsgLines := strings.Split(commitMsg, "\n")[4:]
	commitMsgHeader = commitMsgLines[0]
	commitMsg = strings.Join(commitMsgLines, "\n")

	change := gerrit.ChangeInfo{
		Project: *repoFlag,
		Branch:  *branchFlag,
		Subject: commitMsgHeader,
	}

	// The remained will take a while, so start a thread that prints dots to the console.
	ticker := time.NewTicker(time.Second)
	defer ticker.Stop()
	dotPrinterDone := make(chan bool)
	fmt.Printf("Uploading the change to Gerrit")
	go func() {
		for {
			select {
			case <-dotPrinterDone:
				fmt.Printf(" Done!\n")
				return
			case _ = <-ticker.C:
				fmt.Printf(".")
			}
		}
	}()

	// Create a new gerrit issue.
	newCh, _, err := client.Changes.CreateChange(&change)
	if err != nil {
		return nil
	}

	// Change the full commit message.
	msgBody := gerrit.ChangeEditMessageInput{Message: commitMsg}
	_, err = client.Changes.ChangeCommitMessageInChangeEdit(newCh.ID, &msgBody)
	if err != nil {
		return err
	}

	// Add the file change to the issue.
	_, err = client.Changes.ChangeFileContentInChangeEdit(newCh.ID, fileName, newFileContents)
	if err != nil {
		return err
	}

	// Publish the change.
	_, err = client.Changes.PublishChangeEdit(newCh.ID, "NONE")
	if err != nil {
		return err
	}

        // TODO: Print link to new gerrit change.
	dotPrinterDone <- true
	return nil
}

func main() {
	err := doMain()
	if err != nil {
		fmt.Println(err)
		os.Exit(1)
	}
	os.Exit(0)
}

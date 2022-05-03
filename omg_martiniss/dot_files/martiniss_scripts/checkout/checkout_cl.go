// Opens a vim editor for a given CL. It tries to re-use existing vim
// windows if possible.
package main

import (
	"bytes"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"io/ioutil"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
	"sync"
	// "github.com/moowiz/autocomp"
)

var knownDigest string

func main() {
	if len(os.Args) < 2 {
		fmt.Printf("CL link required\n")
		os.Exit(1)
	}

	clURL := os.Args[1]
	if !strings.HasPrefix(clURL, "https://") {
		fmt.Printf("Bad URL %v: Expected https:// URL", clURL)
		os.Exit(1)
	}
	clURL = strings.Trim(clURL, "/")
	split := strings.Split(clURL, "/")
	id := split[len(split)-1]
	num, err := strconv.Atoi(id)
	if err != nil {
		panic(err)
	}

	// FIXME: Should guess from the thing
	host := "https://chromium-review.googlesource.com"
	wg := &sync.WaitGroup{}
	var clInfo *clInfo
	var changedFiles []string
	wg.Add(2)
	go func() {
		clInfo = getCLInfo(host, num)
		wg.Done()
	}()
	go func() {
		changedFiles = getChangedFiles(host, num)
		wg.Done()
	}()
	wg.Wait()

	path := getRepoPath(clInfo.Project) + string(os.PathSeparator) + changedFiles[0]
	fmt.Printf("Going to %v\n", path)
	//autocomp.EditFile(path)
	os.Exit(0)

	/*
		fileDirectory := filepath.Dir(path)
			tmux := os.Getenv("TMUX")
			if tmux == "" {
				// Change directory to just outside this file
				// NOT MAINTAINED
				fmt.Printf("%v\n", fileDirectory)
			} else {
				// fmt.Printf("path to check %v\n", fileDirectory)
				pathToTmuxID := getPathToTmuxID()
				length := 0
				candidates := []string{}
				for tmuxPath := range pathToTmuxID {
					paths := []string{fileDirectory, tmuxPath}
					pathPrefix := commonPathExcludingHome(paths)
					if pathPrefix == "" {
						continue
					}
					if len(pathPrefix) == length {
						candidates = append(candidates, pathPrefix)
					}
					if len(pathPrefix) > length {
						candidates = []string{pathPrefix}
						tmp := trimPrefix(os.Getenv("HOME"), candidates...)
						if len(tmp[0]) > 0 {
							length = len(pathPrefix)
						} else {
							// Maybe wrong?
							candidates = []string{}
						}
					}
				}
				switch len(candidates) {
				case 0:
					// Make new window
					cmd := exec.Command("tmux", "new-window", "-c", fileDirectory)
					if err := cmd.Run(); err != nil {
						panic(err)
					}
				case 1:
					id := pathToTmuxID[candidates[0]]
					if id == "" {
						fmt.Printf("No tmux window ID found for %v\nValid paths:\n", candidates[0])
						for path := range pathToTmuxID {
							fmt.Printf("  %v\n", path)
						}
						os.Exit(1)
					}
					// fmt.Printf("selecting %v\n", id)
					cmd := exec.Command("tmux", "select-window", "-t", pathToTmuxID[candidates[0]])
					if err := cmd.Run(); err != nil {
						panic(err)
					}
				default:
					fmt.Printf("Candidates\n")
					for _, c := range candidates {
						fmt.Printf("  %v\n", c)
					}
					panic(fmt.Errorf("more than one candidate aaa"))
				}

				cmd := exec.Command("tmux", "send-keys", fmt.Sprintf("git cl checkout %v", os.Args[1]), "Enter", "tmux wait-for -S after_checkout", "Enter")
				if err := cmd.Run(); err != nil {
					panic(err)
				}

				cmd = exec.Command("tmux", "wait-for", "after_checkout")
				if err := cmd.Run(); err != nil {
					panic(err)
				}
			}

			cmd := exec.Command("ovim", path)
			if err := cmd.Run(); err != nil {
				panic(err)
			}
	*/
	os.Exit(0)
}

func getPathToTmuxID() map[string]string {
	rval := map[string]string{}

	cmd := exec.Command("tmux", "list-windows", "-F", "#{window_id} #{pane_current_path}")
	var buf bytes.Buffer
	cmd.Stdout = &buf
	if err := cmd.Run(); err != nil {
		panic(err)
	}

	lines := strings.Split(buf.String(), "\n")
	for _, line := range lines {
		if strings.TrimSpace(line) == "" {
			continue
		}
		// fmt.Printf("line |%v|\n", line)
		split := strings.Split(line, " ")
		rval[split[1]] = split[0]
	}
	return rval
}

/*
var repoMap = map[string]string{
	"chromium/src":         "~/chromium/src",
	"chromium/tools/build": "~/src/build",
}

*/

type clInfo struct {
	Id      string `json:"id"`
	Project string `json:"project"`
}

func getCLInfo(host string, changeID int) *clInfo {
	host = strings.TrimRight(host, "/")
	url := fmt.Sprintf("%s/changes/%d", host, changeID)
	resp, err := http.Get(url)
	if err != nil {
		panic(err)
	}
	defer resp.Body.Close()
	all, err := ioutil.ReadAll(resp.Body)
	if err != nil {
		panic(err)
	}
	all = all[4:]
	info := &clInfo{}
	err = json.NewDecoder(bytes.NewBuffer(all)).Decode(info)
	if err != nil {
		panic(err)
	}
	return info
}

func getChangedFiles(host string, changeID int) []string {
	host = strings.TrimRight(host, "/")
	url := fmt.Sprintf("%s/changes/%d/revisions/current/patch", host, changeID)
	resp, err := http.Get(url)
	if err != nil {
		panic(err)
	}
	defer resp.Body.Close()
	all, err := ioutil.ReadAll(resp.Body)
	if err != nil {
		panic(err)
	}
	data, err := base64.StdEncoding.DecodeString(string(all))
	if err != nil {
		panic(err)
	}
	lines := strings.Split(string(data), "\n")
	files := []string{}
	for _, line := range lines {
		if !strings.HasPrefix(line, "diff --git a") {
			continue
		}
		split := strings.Split(line, "b/")
		files = append(files, split[1])
	}
	return sortByExtension(files)
}

// File extension weight. Higher means we want to open it more.
var extWeight = map[string]int{
	"py":   10,
	"pyl":  5,
	"json": 2,
}

func sortByExtension(files []string) []string {
	sort.Slice(files, func(i, j int) bool {
		return files[i] > files[j]
	})
	return files
}

func getConfigPath() string {
	return expandHome("~/.config/autocomp_repomap.json")
}

// readRepoConfig reads the repository config from local disk
// and returns it as a map of project name to directory on disk.
func readRepoConfig() (rval map[string]string) {
	cfgPath := getConfigPath()
	f, err := os.Open(cfgPath)
	if err != nil {
		panic(err)
	}
	enc := json.NewDecoder(f)
	err = enc.Decode(&rval)
	if err != nil {
		panic(err)
	}
	return
}

// updateRepoConfig
func updateRepoConfig(mapping map[string]string) error {
	cfgPath := getConfigPath()
	f, err := os.Create(cfgPath)
	if err != nil {
		panic(err)
	}
	enc := json.NewEncoder(f)
	return enc.Encode(mapping)
}

func getRepoPath(repoName string) string {
	mapping := readRepoConfig()
	val, ok := mapping[repoName]
	if !ok {
		panic(fmt.Errorf("repo %v not in map\n", repoName))
	}
	return expandHome(val)
}

func expandHome(path string) string {
	if !strings.HasPrefix(path, "~") {
		return path
	}

	home := os.Getenv("HOME")

	return home + path[1:]
}

func commonPathExcludingHome(paths []string) string {
	return commonPrefix(paths...)
}

// trimPrefix removes a prefix from every path given to it, if it's present in the path.
func trimPrefix(prefix string, paths ...string) []string {
	newPaths := make([]string, len(paths))
	for i, path := range paths {
		if strings.HasPrefix(path, prefix) {
			newPaths[i] = path[len(prefix):]
			continue
		}
		newPaths[i] = path
	}

	return newPaths
}
func commonPrefix(paths ...string) string {
	// Handle special cases.
	switch len(paths) {
	case 0:
		return ""
	case 1:
		return filepath.Clean(paths[0])
	}

	c := []byte(filepath.Clean(paths[0]))

	c = append(c, os.PathSeparator)

	// Ignore the first path since it's already in c
	for _, v := range paths[1:] {
		// Clean up each path before testing it
		v = filepath.Clean(v) + string(os.PathSeparator)

		// Find the first non-common byte and truncate c
		if len(v) < len(c) {
			c = c[:len(v)]
		}
		for i := 0; i < len(c); i++ {
			if v[i] != c[i] {
				c = c[:i]
				break
			}
		}
	}

	// Remove trailing non-separator characters and the final separator
	for i := len(c) - 1; i >= 0; i-- {
		if c[i] == os.PathSeparator {
			c = c[:i]
			break
		}
	}

	return string(c)
}

package main

import (
	"bufio"
	"bytes"
	"fmt"
	"io/ioutil"
	"os"
	"os/exec"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
)

func main() {
	if len(os.Args) < 2 {
		fmt.Printf("Path required")
		os.Exit(1)
	}

	originalPath, err := filepath.Abs(filepath.Clean(os.Args[1]))
	if err != nil {
		panic(err)
	}
	res := findCachedFiles(originalPath)
	filtered := filterPaths(res, originalPath)
	if len(filtered) == 0 {
		fmt.Printf("Opening new editor...\n")
		cmd := exec.Command("gvim", originalPath)
		if err := cmd.Run(); err != nil {
			panic(err)
		}
		os.Exit(0)
	}
	pids := findFilePIDs(filtered)
	if len(pids) == 1 {
		for _, pid := range pids {
			openPID(pid)
			os.Exit(0)
		}
	}
	i := 0
	paths := make([]string, len(pids))
	for path := range pids {
		paths[i] = path
		i++
	}
	sort.Strings(paths)
	for i, path := range paths {
		rel, err := filepath.Rel(originalPath, path)
		if err != nil {
			panic(err)
		}
		fmt.Printf("[%v]: %v\n", i, rel)
	}

	num := -1
	reader := bufio.NewReader(os.Stdin)
	for num < 0 || num > len(paths) {
		fmt.Printf("Multiple possible files, pick one: ")
		text, err := reader.ReadString('\n')
		if err != nil {
			panic(err)
		}
		text = strings.TrimSpace(text)
		num, err = strconv.Atoi(strings.TrimSpace(text))
		if err != nil {
			panic(err)
		}
		if num < 0 || num > len(paths) {
			fmt.Printf("Bad number: %v\n", num)
		}
	}
	openPID(pids[paths[num]])
	os.Exit(0)
}

func openPID(pid int) {
	id := getWindowID(pid)
	cmd := exec.Command("xdotool", "windowactivate", strconv.Itoa(id))
	if err := cmd.Run(); err != nil {
		panic(err)
	}
}

func getWindowID(pid int) int {
	cmd := exec.Command("xdotool", "search", "--pid", strconv.Itoa(pid))
	var buf bytes.Buffer
	cmd.Stdout = &buf
	if err := cmd.Run(); err != nil {
		panic(err)
	}
	allStrs := strings.Split(buf.String(), "\n")
	num, err := strconv.Atoi(strings.TrimSpace(allStrs[len(allStrs)-2]))
	if err != nil {
		panic(err)
	}
	return num
}

func filterPaths(paths []string, basePath string) []string {
	result := []string{}
	for _, path := range paths {
		if strings.HasPrefix(path, basePath) {
			result = append(result, path)
		}
	}

	return result
}

func getCacheLocation() string {
	HOME := os.Getenv("HOME")

	return filepath.Join(HOME, ".vim", "cache")
}

func findCachedFiles(path string) []string {
	files, err := ioutil.ReadDir(getCacheLocation())
	if err != nil {
		panic(err)
	}

	parsed := []string{}
	for _, file := range files {
		path := strings.Replace(file.Name(), "%", string(filepath.Separator), -1)
		if !strings.HasSuffix(path, ".swp") {
			panic(fmt.Errorf("Weird cache file %s", path))
		}
		path = path[:len(path)-len(".swp")]
		parsed = append(parsed, path)
	}

	return parsed
}

func findFilePIDs(validFiles []string) map[string]int {
	sub, err := filepath.Glob("/proc/*/fd/*")
	if err != nil {
		panic(err)
	}
	files := map[string]int{}
	cacheLoc := getCacheLocation()
	for _, path := range sub {
		_, err := os.Stat(path)
		if err != nil {
			_, ok := err.(*os.PathError)
			if ok {
				continue
			}
			panic(err)
		}
		target, err := filepath.EvalSymlinks(path)
		if os.IsNotExist(err) {
			continue
		}
		if err != nil {
			panic(err)
		}
		if !strings.HasPrefix(target, cacheLoc) {
			continue
		}
		target = target[len(cacheLoc)+1:]
		target = strings.Replace(target, "%", "/", -1)
		target = target[:len(target)-len(".swp")]
		for _, validPath := range validFiles {
			if validPath == target {
				num, err := strconv.Atoi(strings.Split(path, "/")[2])
				if err != nil {
					panic(err)
				}
				files[target] = num
				break
			}
		}
	}

	return files
}

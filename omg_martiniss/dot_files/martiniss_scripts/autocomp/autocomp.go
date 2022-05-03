package autocomp

import (
	"bufio"
	"bytes"
	"crypto/sha256"
	"fmt"
	"io"
	"io/ioutil"
	"os"
	"os/exec"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
	"time"
)

// func KeepFresh(args []string, known string) {
//
// 	_, path, _, _ := runtime.Caller(1)
// 	curDir := filepath.Dir(path)
// 	originalDir, err := os.Getwd()
// 	if err != nil {
// 		panic(err)
// 	}
// 	os.Chdir(curDir)
// 	defer func() { os.Chdir(originalDir) }()
//
// 	digest, err := getDepDigest(path)
// 	if err != nil {
// 		panic(err)
// 	}
//
// 	if len(args) == 2 && args[1] == "getdigest" {
// 		fmt.Printf("%v", digest)
// 		os.Exit(0)
// 	}
// 	if digest != known {
//
// 		fmt.Printf("Recompiling...\n")
// 		cmd := exec.Command(filepath.Join(filepath.Dir(path), "compile.sh"))
// 		if out, err := cmd.CombinedOutput(); err != nil {
// 			fmt.Printf("Error recompiling: %v\n", string(out))
// 			panic(err)
// 		}
// 		cmd = exec.Command(strings.Split(path, ".")[0], args[1:]...)
// 		cmd.Stdin = os.Stdin
// 		cmd.Stdout = os.Stdout
// 		cmd.Stderr = os.Stderr
// 		err := cmd.Run()
// 		if err == nil {
// 			os.Exit(0)
// 		}
// 		e := err.(*exec.ExitError)
// 		os.Exit(e.ExitCode())
// 	}
// }

// GetTransitiveLastUpdated gets the most recent time any dependency of a given golang module has been
// updated.
func GetTransitiveLastUpdated(path string) (time.Time, error) {
	/*
		cmd := exec.Command("go", "list", "-f", "'{{ .Deps }}'", path)
		out, err := cmd.CombinedOutput()
		if err != nil {
			log.Fatalf("Err while getting dependencies: %v", string(out))
			return time.Time{}, err
		}
		s := string(out)
		s = strings.TrimSpace(s)
		s = s[2 : len(s)-2]
	*/

	args := append([]string{"list", "-f", "{{.Standard}}|{{.Dir}}|{{.GoFiles}}"}, "-deps", path)
	// HACK
	//args = append(args, "main")
	cmd := exec.Command("go", args...)
	//fmt.Printf("args %v\n", cmd.Args)
	out, err := cmd.Output()
	if err != nil {
		ee, ok := err.(*exec.ExitError)
		if ok {
			fmt.Printf("stderr: \"%v\"\n", string(ee.Stderr))
			fmt.Printf("stdout: %v\n", string(out))
		}
		return time.Time{}, err
	}
	s := string(out)
	s = strings.TrimSpace(s)
	allFiles := []string{}
	for _, line := range strings.Split(s, "\n") {
		sp := strings.Split(line, "|")
		// Standard library, we don't care.
		if sp[0] == "true" {
			continue
		}
		dir := sp[1]
		files_s := sp[2]
		files_s = files_s[1 : len(files_s)-1]
		files := strings.Split(files_s, " ")
		for _, f := range files {
			allFiles = append(allFiles, dir+"/"+f)
		}
	}
	latestTime := time.Time{}
	for _, f := range allFiles {
		t := getFileTime(f)
		if latestTime.Before(t) {
			latestTime = t
		}
	}
	return latestTime, nil
}

func strDigest(val string) []byte {
	hasher := sha256.New()
	hasher.Write([]byte(val))
	return hasher.Sum(nil)
}

func fileDigest(path string) string {
	f, err := os.Open(path)
	if err != nil {
		panic(err)
	}
	defer f.Close()

	h := sha256.New()
	if _, err := io.Copy(h, f); err != nil {
		panic(err)
	}

	return fmt.Sprintf("%x", h.Sum(nil))
}

func getCacheLocation() string {
	HOME := os.Getenv("HOME")

	return filepath.Join(HOME, ".vim", "cache")
}

func findCachedFiles() []string {
	files, err := ioutil.ReadDir(getCacheLocation())
	if err != nil {
		panic(err)
	}

	parsed := []string{}
	for _, file := range files {
		path := strings.Replace(file.Name(), "%", string(filepath.Separator), -1)
		if strings.HasSuffix(path, ".swo") || strings.HasSuffix(path, ".swn") {
			// Weird unnamed files I think
			continue
		}
		if !strings.HasSuffix(path, ".swp") {
			panic(fmt.Errorf("Weird cache file %s", path))
		}
		path = path[:len(path)-len(".swp")]
		parsed = append(parsed, path)
	}

	return parsed
}

func findFilePIDs(validFiles []string) map[string]int {
	// Probably can make this faster than scanning every process
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
		target = strings.TrimPrefix(target, cacheLoc)
		target = strings.TrimSuffix(target, ".swp")
		target = strings.Replace(target, "%", "/", -1)
		for _, validPath := range validFiles {
			if validPath == target {
				pid, err := strconv.Atoi(strings.Split(path, "/")[2])
				if err != nil {
					panic(err)
				}
				files[target] = pid
				break
			}
		}
	}

	return files
}

func EditFile(path string) {
	originalPath, err := filepath.Abs(filepath.Clean(path))
	if err != nil {
		panic(err)
	}
	originalPath, err = filepath.EvalSymlinks(originalPath)
	if err != nil {
		panic(err)
	}
	/*
		info, err := os.Stat(originalPath)
		if os.IsNotExist(err) {
			panic(err)
		}
		pathIsDir := info.IsDir()
	*/

	cached := findCachedFiles()
	filtered := filterPaths(cached, originalPath)
	if len(filtered) == 0 {
		fmt.Printf("Opening new editor...\n")
		cmd := exec.Command("vim", originalPath)
		cmd.Stdin = os.Stdin
		cmd.Stdout = os.Stdout
		cmd.Stderr = os.Stderr
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
	/*
	   if !pathIsDir {
	   log.Fatalf("Path %v is not a directory", originalPath)
	   }*/
	// Paths relative to the original path. This assumes it's a directory.
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

func filterPaths(paths []string, basePath string) []string {
	result := []string{}
	for _, path := range paths {
		if strings.HasPrefix(path, basePath) {
			result = append(result, path)
		}
	}

	return result
}

func getFileTime(path string) time.Time {
	data, err := os.Stat(path)
	if err != nil {
		panic(err)
	}
	return data.ModTime()
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

func openPID(pid int) {
	if false {
		id := getWindowID(pid)
		cmd := exec.Command("xdotool", "windowactivate", strconv.Itoa(id))
		if err := cmd.Run(); err != nil {
			panic(err)
		}
	} else {
		// Need to figure this out
		return
	}
}

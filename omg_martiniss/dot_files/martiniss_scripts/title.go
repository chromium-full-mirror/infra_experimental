package main

import (
	"flag"
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

var path string

func main() {
	flag.StringVar(&path, "currentPane", "", "current path")
	flag.Parse()
	s, err := filepath.Abs(path)
	if err != nil {
		panic(err)
	}
	path = filepath.Clean(s)
	homeDir := os.Getenv("HOME")
	rel, err := filepath.Rel(homeDir, path)
	if err != nil {
		panic(err)
	}
	parts := append([]string{"~"}, strings.Split(rel, "/")...)
	if len(parts) > 5 {
		parts = []string{parts[0], parts[1], parts[2], "..", parts[len(parts)-2], parts[len(parts)-1]}
	}
	fmt.Printf("%v", strings.Join(parts, "/"))
}

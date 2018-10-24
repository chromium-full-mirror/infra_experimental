package main

import (
	"fmt"
	"os"

	"github.com/moowiz/autocomp"
)

func main() {
	autocomp.KeepFresh()
	if len(os.Args) < 2 {
		fmt.Printf("Path required")
		os.Exit(1)
	}

	fmt.Printf("got file %v", os.Args[1])
	os.Exit(0)
}

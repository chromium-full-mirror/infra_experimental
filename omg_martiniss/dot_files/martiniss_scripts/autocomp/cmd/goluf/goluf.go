package main

// goluf checks if a go package has been modified before a certain time.

import (
	"fmt"
	"os"
	"strconv"
	"time"

	"github.com/moowiz/autocomp"
)

func main() {
	if len(os.Args) != 3 {
		fmt.Printf("Expected 3 args but got %v\n", os.Args)
		os.Exit(1)
	}

	lastMod, err := autocomp.GetTransitiveLastUpdated(os.Args[1])
	if err != nil {
		panic(err)
	}
	num, err := strconv.Atoi(os.Args[2])
	if err != nil {
		panic(err)
	}
	cmpTime := time.Unix(int64(num), 0)
	if lastMod.After(cmpTime) {
		os.Exit(1)
	}
	os.Exit(0)
}

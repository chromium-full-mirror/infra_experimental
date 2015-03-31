// Copyright 2015 The Chromium Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

package main

// Limitations:
// - Doesn't handle nullable fields very well.  You may end up with multiple
//   structs for the same actual field type.
// - Maps of maps: it tries to handle this case but ends up with a blank
//   struct type name. Not a problem for alerts.json since it only has one
//   of these.

import (
	"encoding/json"
	"fmt"
	"os"
	"reflect"
	"sort"
	"strings"
)

// Rules:
// If it's a primitive type, just make it a field on the struct.
// If it's an array of a primitive type, make it an array on the struct.
// If it's a map of string to interface:
// 	Build a canonicalized struct spec string out of it (recursively) and see
// 	if there is already a named struct spec for it.
type field struct {
	name, alias, t string
}

type fieldArr []field

// sort.Sortable interface
func (a fieldArr) Len() int           { return len(a) }
func (a fieldArr) Swap(i, j int)      { a[i], a[j] = a[j], a[i] }
func (a fieldArr) Less(i, j int) bool { return fmt.Sprintf("%v", a[i]) < fmt.Sprintf("%v", a[j]) }

var (
	structs      = make(map[string]string)
	structFields = make(map[string][]field)
)

func getStructName(f []field, def string) string {
	fs := []string{}
	for _, v := range f {
		fs = append(fs, fmt.Sprintf("%v", v))
	}
	k := strings.Join(fs, ",")
	if s, ok := structs[k]; ok {
		return s
	}

	structs[k], _ = fieldName(def)
	if def == "" {
		structs[k] = fmt.Sprintf("StructType%v", len(structs))
	}
	structFields[structs[k]] = f
	return structs[k]
}

// returns map[string]SomeType{}
func processMap(a map[string]interface{}) string {
	lastValueType := ""
	for k, v := range a {
		vt := reflect.TypeOf(v).String()
		nextValueType := ""
		switch vt {
		case "map[string]interface {}":
			m := v.(map[string]interface{})
			fs, isMap := fields(m)
			if isMap {
				nextValueType = fmt.Sprintf("map[string]%s", processMap(m))
			} else {
				nextValueType = getStructName(fs, k)
			}
		case "[]interface {}":
			// FIXME: This should do something different. Set nextValueType to
      // something.
			nextValueType = "map[string][]interface{}"
		default:
			nextValueType = vt
		}
		if lastValueType != "" && nextValueType != lastValueType {
			// Homogenous collection. Give up.
			return "map[string]interface{}"
		}
		lastValueType = nextValueType
	}

	return fmt.Sprintf("map[string]%s", lastValueType)
}

// Given a parsed json blob, return a struct definition that corresponds to it.
// Field names will follow Go conventions rather than the json conventions.
func fields(a map[string]interface{}) ([]field, bool) {
	var out []field
	for k, v := range a {
		if v == nil {
			// This should accumulate the field names at least.

			continue
		}
		n, isField := fieldName(k)
		if !isField {
			return nil, true // This is a map, not a struct.
		}
		t := reflect.TypeOf(v).String()
		switch t {
		case "[]interface {}":
			ar := v.([]interface{})
			if len(ar) == 0 {
				continue
			}
			at := reflect.TypeOf(ar[0]).String()
			if at == "map[string]interface {}" {
				rf, isMap := fields(ar[0].(map[string]interface{}))
				if isMap {
					fmt.Printf("1 is a map: %s\n", k)
				} else {
					out = append(out, field{n, k, fmt.Sprintf("[]%v", getStructName(rf, k))})
				}
			} else {
				out = append(out, field{n, k, fmt.Sprintf("[]%v", at)})
			}
		case "map[string]interface {}":
			m, _ := v.(map[string]interface{})
			rf, isMap := fields(m)
			if isMap {
				fmt.Printf("2 is a map: %s\n", k)
				out = append(out, field{n, k, processMap(m)})
			} else {
				out = append(out, field{n, k, getStructName(rf, k)})
			}
		default:
			out = append(out, field{n, k, t})
		}
	}

	sort.Sort(fieldArr(out))
	return out, false
}

func fieldName(s string) (string, bool) {
	if strings.IndexAny(s, " -;.:()[]") != -1 {
		return "", false
	}

	parts := strings.Split(s, "_")
	var out []string
	for _, p := range parts {
		out = append(out, strings.Title(p))
	}

	return strings.Join(out, ""), true
}

func printStruct(n string, ff []field) {
	fmt.Printf("type %s struct {\n", n)
	for _, f := range ff {
		fmt.Printf("\t%s\t%s\t`json:\"%s\"`\n", f.name, f.t, f.alias)
	}
	fmt.Printf("}\n")
}

func main() {
	dec := json.NewDecoder(os.Stdin)
	var f map[string]interface{}
	if err := dec.Decode(&f); err != nil {
		fmt.Printf("Error: %v\n", err)
		return
	}
	fs, isMap := fields(f)

	if isMap {
		fmt.Printf("This is a map. Sorry.\n")
	} else {
		printStruct("MainStruct", fs)
	}

	for k, v := range structFields {
		printStruct(k, v)
	}
}

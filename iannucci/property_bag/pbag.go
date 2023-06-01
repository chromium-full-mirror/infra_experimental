package propertybag

import (
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"sort"

	ds "go.chromium.org/luci/gae/service/datastore"
)

// Record is an indexed property bag with a string value attached.
//
// This has a datastore ID which is a sha256 of the sorted Tags.
// In other words, two Record objects with the same set of Tags will
// also have the same identity.
type Record struct {
	// Key, value mapping; The key:value pairs are searchable in datastore.
	//
	// Each key will turn into a property name, and the value will be its
	// (indexed) property value.
	Tags map[string]string

	// Value is an unindexed blob attached to this Record.
	//
	// Presumably this would be something semi-structured like JSON.
	Value string
}

// We want to fully control how the datastore library serializes our
// model, so implement the full MetaGetterSetter interface.
var _ ds.MetaGetterSetter = (*Record)(nil)

// Load implements PropertyLoadSaver.
//
// When datastore loads a raw PropertyMap for our model type, it will
// invoke Load with the raw PropertyMap.
//
// We store the __value property into our Value field, and all non-__key__
// properties into Tags.
func (r *Record) Load(pm ds.PropertyMap) error {
	r.Tags = make(map[string]string, len(pm)-2) // -2 for __key__ and __value
	for key, values := range pm {
		strVal := values.Slice()[0].Value().(string)
		switch key {
		case "__key__":
			// ignore
		case "__value":
			r.Value = strVal
		default:
			r.Tags[key] = strVal
		}
	}
	return nil
}

// computeHash generates a stable sha256 for the given string map.
func computeHash(tags map[string]string) string {
	keys := make([]string, 0, len(tags))
	for key := range tags {
		keys = append(keys, key)
	}
	sort.Strings(keys)

	s := sha256.New()
	for _, key := range keys {
		fmt.Fprintf(s, "%s:%s|", key, tags[key])
	}
	return hex.EncodeToString(s.Sum(nil))
}

// computeID prepends "1:" to the computeHash of r.Tags, just into
// case we need to change the key schema later.
func (r *Record) computeID() string {
	return "1:" + computeHash(r.Tags)
}

// addMeta adds $kind and $id to an existing PropertyMap
func (r *Record) addMeta(pm ds.PropertyMap) {
	pm["$kind"] = ds.MkPropertyNI("Record")
	pm["$id"] = ds.MkPropertyNI(r.computeID())
}

// Save implements PropertyLoadSaver.
//
// When datastore needs to save our Model, it calls Save to serialize it
// into a PropertyMap.
func (r *Record) Save(withMeta bool) (ds.PropertyMap, error) {
	ret := make(ds.PropertyMap, len(r.Tags)+3)
	if withMeta {
		r.addMeta(ret)
	}
	ret["__value"] = ds.MkPropertyNI(r.Value)
	for tag, value := range r.Tags {
		ret[tag] = ds.MkProperty(value)
	}
	return ret, nil
}

// GetMeta implements MetaGetterSetter.
//
// This returns the value of metadata on our Record, specifically "$id" and
// "$kind", which datastore uses to calculate a Key for our model.
func (r *Record) GetMeta(key string) (interface{}, bool) {
	switch key {
	case "kind":
		return "Record", true
	case "id":
		return r.computeID(), true
	}
	return nil, false
}

// GetAllMeta implements MetaGetterSetter.
func (r *Record) GetAllMeta() ds.PropertyMap {
	ret := make(ds.PropertyMap, 2)
	r.addMeta(ret)
	return ret
}

// SetMeta implements MetaGetterSetter.
//
// However, we don't have any settable metadata on our Record model.
func (r *Record) SetMeta(key string, val interface{}) bool {
	// no settable metadata
	return false
}

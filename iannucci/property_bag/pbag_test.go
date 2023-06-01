package propertybag

import (
	"context"
	"testing"

	"go.chromium.org/luci/gae/impl/memory"
	ds "go.chromium.org/luci/gae/service/datastore"
)

func TestRecord(t *testing.T) {
	// memory.Use sets the in-memory datastore mock in the context.
	ctx := memory.Use(context.Background())
	// This sets "fully-consistent" mode in the emulated datastore; This should
	// match the _actual_ behavior of firestore-in-datastore-mode though.
	ds.GetTestable(ctx).Consistent(true)

	// Make an arbitrary Record
	r := &Record{
		Tags: map[string]string{
			"device": "cros",
			"board":  "b1",
		},
		Value: "arbitrary stuff",
	}
	// Note that the datastore library can correctly compute the Key for this Record.
	if key := ds.KeyForObj(ctx, r); !key.Equal(ds.MakeKey(ctx, "Record", "1:ae35639d8f4d9952d8cf69e2a445b8bc01a838d9d58a6ed4d731db66f0daa3dc")) {
		t.Fatal("got bad key:", key)
	}

	// We can put the Record into the datastore.
	if err := ds.Put(ctx, r); err != nil {
		t.Fatal(err)
	}

	// All three of these queries will yield the same Record.
	queries := []*ds.Query{
		ds.NewQuery("Record").Eq("device", "cros"),
		ds.NewQuery("Record").Eq("device", "cros").Eq("board", "b1"),
		ds.NewQuery("Record").Eq("board", "b1"),
	}
	for _, query := range queries {
		records := []*Record{}
		if err := ds.GetAll(ctx, query, &records); err != nil {
			t.Fatal(err)
		}
		if len(records) != 1 {
			t.Fatal("bad number of records:", len(records), query)
		}

		if records[0].Value != "arbitrary stuff" {
			t.Fatal("got the wrong Record", query)
		}
	}

	// However this query won't see it
	q := ds.NewQuery("Record").Eq("device", "norp")
	count, err := ds.Count(ctx, q)
	if err != nil {
		t.Fatal("query failed:", q)
	}
	if count != 0 {
		t.Fatal("got results for the bad query:", q)
	}
}

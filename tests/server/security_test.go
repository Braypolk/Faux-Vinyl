package main

import (
	"crypto/sha256"
	"encoding/hex"
	"strings"
	"testing"

	"golang.org/x/crypto/pbkdf2"
)

func TestMalformedPasswordHashesCannotAuthenticate(t *testing.T) {
	for _, encoded := range []string{
		"pbkdf2:sha256:1000$salt$",
		"pbkdf2:sha256:1000$salt$00",
		"pbkdf2:sha256:1000$salt$not-hex",
		"pbkdf2:sha256:1000$$" + strings.Repeat("00", 32),
		"pbkdf2:sha256:1000$salt$" + strings.Repeat("00", 129),
		"scrypt:16:1:1$salt$",
	} {
		if checkPassword(encoded, "anything") {
			t.Fatal("Malformed password hash accepted a password")
		}
	}
	want := pbkdf2.Key([]byte("correct"), []byte("salt"), 1000, 32, sha256.New)
	encoded := "pbkdf2:sha256:1000$salt$" + hex.EncodeToString(want)
	if !checkPassword(encoded, "correct") || checkPassword(encoded, "wrong") {
		t.Fatal("Valid password verification changed")
	}
}

func TestCreatingDuplicateCardCannotReplaceItsNFCMapping(t *testing.T) {
	a := testApp(t)
	original := Card{ID: "fixed-id", Title: "Original", URI: "spotify:album:1111111111111111111111"}
	if err := a.store.create(original); err != nil {
		t.Fatal(err)
	}
	before, err := a.store.cards("custom")
	if err != nil {
		t.Fatal(err)
	}
	other := Card{ID: original.ID, Title: "Replacement", URI: "spotify:album:2222222222222222222222"}
	if err := a.store.create(other); err == nil {
		t.Fatal("Duplicate identity was accepted")
	}
	got, err := a.store.card(original.ID)
	if err != nil || got.Title != original.Title || got.URI != original.URI {
		t.Fatal("Existing NFC mapping changed", got, err)
	}
	after, err := a.store.cards("custom")
	if err != nil || orderVersion(cardIDs(before)) != orderVersion(cardIDs(after)) {
		t.Fatal("Failed creation changed shelf order", err)
	}
}

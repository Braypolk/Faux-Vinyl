package main

import (
	"net/url"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestAutomaticDevicePriorityUsesInstallationSettings(t *testing.T) {
	devices := []Device{{ID: "desk", Name: "Desk Speaker"}, {ID: "kitchen", Name: "Kitchen Speaker"}}
	if _, err := chooseDevice(devices, "auto", ""); err == nil {
		t.Fatal("Unconfigured devices must require a choice")
	}
	got, err := chooseDevice(devices, "auto", "Offline Speaker\nKitchen Speaker\nDesk Speaker")
	if err != nil || got.ID != "kitchen" {
		t.Fatal(got, err)
	}
	devices[0].Active = true
	got, err = chooseDevice(devices, "auto", "Kitchen Speaker")
	if err != nil || got.ID != "desk" {
		t.Fatal("Active device must win", got, err)
	}
	got, err = chooseDevice(devices, "Kitchen Speaker", "Desk Speaker")
	if err != nil || got.ID != "kitchen" {
		t.Fatal("Explicit device must win", got, err)
	}
	got, err = chooseDevice(devices[:1], "auto", "")
	if err != nil || got.ID != "desk" {
		t.Fatal("Sole device unavailable", got, err)
	}
}

func TestLocalDeviceDefaultsDoNotOverwriteSavedPreferences(t *testing.T) {
	dir := t.TempDir()
	s, err := openStore(dir)
	if err != nil {
		t.Fatal(err)
	}
	defer s.db.Close()
	file := filepath.Join(dir, "preferences.json")
	if err = s.importPreferences(file); err != nil {
		t.Fatal(err)
	}
	if err = os.WriteFile(file, []byte(`{"device_priority":["Kitchen Speaker","Desk Speaker"]}`), 0600); err != nil {
		t.Fatal(err)
	}
	if err = s.set("device", "Chosen Speaker"); err != nil {
		t.Fatal(err)
	}
	if err = s.importPreferences(file); err != nil {
		t.Fatal(err)
	}
	if s.setting("device_priority", "") != "Kitchen Speaker\nDesk Speaker" || s.setting("device", "") != "Chosen Speaker" {
		t.Fatal("Local defaults lost or explicit device changed")
	}
	if err = s.set("device_priority", ""); err != nil {
		t.Fatal(err)
	}
	if err = s.importPreferences(file); err != nil {
		t.Fatal(err)
	}
	if s.setting("device_priority", "missing") != "" {
		t.Fatal("Intentional empty priority was overwritten")
	}
}

func TestDevicePrioritySettingsValidationAndPersistence(t *testing.T) {
	a := testApp(t)
	b := &browser{a: a}
	csrf := signIn(t, b)
	form := url.Values{"csrf": {csrf}, "device": {"auto"}, "device_priority": {"Kitchen Speaker\nDesk Speaker"}}
	if w := b.request("POST", "/settings", form, nil); w.Code != 303 {
		t.Fatal(w.Code, w.Body.String())
	}
	if page := b.request("GET", "/settings", nil, nil).Body.String(); !strings.Contains(page, "Kitchen Speaker\nDesk Speaker") {
		t.Fatal("Saved priority missing")
	}
	form.Set("device_priority", strings.Repeat("Speaker\n", 21))
	if w := b.request("POST", "/settings", form, nil); w.Code != 400 {
		t.Fatal("Oversized priority accepted", w.Code)
	}
	if a.store.setting("device_priority", "") != "Kitchen Speaker\nDesk Speaker" {
		t.Fatal("Invalid submission changed preferences")
	}
	other, err := openStore(a.cfg.DataDir)
	if err != nil {
		t.Fatal(err)
	}
	defer other.db.Close()
	if other.setting("device_priority", "") != "Kitchen Speaker\nDesk Speaker" {
		t.Fatal("Priority did not persist")
	}
}

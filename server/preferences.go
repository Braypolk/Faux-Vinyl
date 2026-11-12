package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"strings"
	"unicode/utf8"
)

func validDevicePriority(names []string) bool {
	if len(names) > 20 {
		return false
	}
	for _, name := range names {
		if !utf8.ValidString(name) || utf8.RuneCountInString(name) > 200 {
			return false
		}
	}
	return true
}

// Import local defaults once. Saved preferences, including an intentionally
// empty priority list, always take precedence on subsequent starts.
func (s *Store) importPreferences(file string) error {
	raw, err := os.ReadFile(file)
	if os.IsNotExist(err) {
		return nil
	}
	if err != nil {
		return err
	}
	var preferences struct {
		DevicePriority []string `json:"device_priority"`
	}
	d := json.NewDecoder(bytes.NewReader(raw))
	d.DisallowUnknownFields()
	if err = d.Decode(&preferences); err != nil {
		return fmt.Errorf("invalid preferences: %w", err)
	}
	if d.Decode(new(any)) != io.EOF || !validDevicePriority(preferences.DevicePriority) {
		return fmt.Errorf("invalid device preferences")
	}
	if preferences.DevicePriority != nil && s.setting("device_priority", nil) == nil {
		return s.set("device_priority", strings.Join(preferences.DevicePriority, "\n"))
	}
	return nil
}

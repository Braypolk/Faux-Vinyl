package main

import (
	"encoding/json"
	"errors"
	"net/http"
	"strings"
)

func wantsJSON(r *http.Request) bool {
	for _, part := range strings.Split(r.Header.Get("Accept"), ",") {
		if strings.TrimSpace(strings.SplitN(part, ";", 2)[0]) == "application/json" {
			return true
		}
	}
	return false
}
func writeJSON(w http.ResponseWriter, status int, value any) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(value)
}
func (a *App) saveShelfOrder(w http.ResponseWriter, r *http.Request, s *Session) {
	e := a.store.saveOrder(r.PostForm["card_id"], r.PostForm.Get("order_version"))
	if e != nil {
		switch {
		case errors.Is(e, errOrderConflict):
			a.fail(w, r, s, 409, e.Error())
		case errors.Is(e, errInvalidOrder):
			a.fail(w, r, s, 400, e.Error())
		default:
			panic(e)
		}
		return
	}
	s.Sort = "custom"
	a.cookie(w, s)
	if wantsJSON(r) {
		writeJSON(w, 200, map[string]string{"status": "saved", "order_version": orderVersion(r.PostForm["card_id"])})
		return
	}
	s.Notice = "Shelf order saved."
	a.redirect(w, r, s, "/?sort=custom")
}

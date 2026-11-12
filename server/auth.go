package main

import (
	"bytes"
	"compress/zlib"
	"crypto/hmac"
	"crypto/rand"
	"crypto/sha1"
	"crypto/sha256"
	"crypto/sha512"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"golang.org/x/crypto/pbkdf2"
	"golang.org/x/crypto/scrypt"
	"hash"
	"io"
	"net/http"
	"strconv"
	"strings"
	"time"
)

var b64 = base64.RawURLEncoding

func randomToken(n int) string {
	b := make([]byte, n)
	if _, e := rand.Read(b); e != nil {
		panic(e)
	}
	return b64.EncodeToString(b)
}
func mac(key []byte, value string) []byte {
	h := hmac.New(sha256.New, key)
	h.Write([]byte(value))
	return h.Sum(nil)
}
func equal(a, b string) bool { return hmac.Equal([]byte(a), []byte(b)) }

type Session struct {
	Auth   string `json:"auth,omitempty"`
	CSRF   string `json:"csrf"`
	Sort   string `json:"shelf_sort,omitempty"`
	Notice string `json:"notice,omitempty"`
	Exp    int64  `json:"exp"`
}

func (a *App) readSession(r *http.Request) Session {
	var s Session
	c, e := r.Cookie("fauxvinyl_session")
	if e != nil {
		return s
	}
	value := c.Value
	if strings.HasPrefix(value, "v1.") {
		p := strings.Split(value, ".")
		if len(p) != 3 {
			return s
		}
		sig, e := b64.DecodeString(p[2])
		if e != nil || !hmac.Equal(sig, mac(a.key, "session:"+p[1])) {
			return s
		}
		raw, e := b64.DecodeString(p[1])
		if e != nil || len(raw) > 16384 || json.Unmarshal(raw, &s) != nil || s.Exp < time.Now().Unix() {
			return Session{}
		}
		return s
	}
	// Accept existing Flask sessions during migration, including compressed cookies.
	i := strings.LastIndexByte(value, '.')
	if i < 0 {
		return s
	}
	signed := value[:i]
	sig, e := b64.DecodeString(value[i+1:])
	if e != nil {
		return s
	}
	h := hmac.New(sha1.New, a.key)
	h.Write([]byte("cookie-session"))
	h2 := hmac.New(sha1.New, h.Sum(nil))
	h2.Write([]byte(signed))
	if !hmac.Equal(sig, h2.Sum(nil)) {
		return s
	}
	j := strings.LastIndexByte(signed, '.')
	if j < 0 {
		return s
	}
	ts, e := b64.DecodeString(signed[j+1:])
	if e != nil || len(ts) > 8 {
		return s
	}
	var issued int64
	for _, b := range ts {
		issued = issued<<8 | int64(b)
	}
	age := time.Now().Unix() - issued
	if age < -60 || age > 90*86400 {
		return s
	}
	payload := signed[:j]
	compressed := strings.HasPrefix(payload, ".")
	payload = strings.TrimPrefix(payload, ".")
	raw, e := b64.DecodeString(payload)
	if e != nil {
		return s
	}
	if compressed {
		z, e := zlib.NewReader(bytes.NewReader(raw))
		if e != nil {
			return s
		}
		raw, e = io.ReadAll(io.LimitReader(z, 16385))
		z.Close()
		if e != nil {
			return s
		}
	}
	if len(raw) > 16384 || json.Unmarshal(raw, &s) != nil {
		return Session{}
	}
	return s
}
func (a *App) cookie(w http.ResponseWriter, s *Session) {
	s.Exp = time.Now().Add(90 * 24 * time.Hour).Unix()
	raw, _ := json.Marshal(s)
	p := b64.EncodeToString(raw)
	http.SetCookie(w, &http.Cookie{Name: "fauxvinyl_session", Value: "v1." + p + "." + b64.EncodeToString(mac(a.key, "session:"+p)), Path: "/", MaxAge: 90 * 86400, Secure: !a.cfg.Dev, HttpOnly: true, SameSite: http.SameSiteLaxMode})
}
func checkPassword(encoded, password string) bool {
	p := strings.Split(encoded, "$")
	if len(p) != 3 || len(password) > 4096 {
		return false
	}
	scheme := strings.Split(p[0], ":")
	want, e := hex.DecodeString(p[2])
	if e != nil {
		return false
	}
	var got []byte
	switch scheme[0] {
	case "pbkdf2":
		if len(scheme) != 3 {
			return false
		}
		n, e := strconv.Atoi(scheme[2])
		if e != nil || n < 1 || n > 10000000 {
			return false
		}
		var h func() hash.Hash
		switch scheme[1] {
		case "sha256":
			h = sha256.New
		case "sha512":
			h = sha512.New
		default:
			return false
		}
		got = pbkdf2.Key([]byte(password), []byte(p[1]), n, len(want), h)
	case "scrypt":
		if len(scheme) != 4 {
			return false
		}
		n, e1 := strconv.Atoi(scheme[1])
		r, e2 := strconv.Atoi(scheme[2])
		p2, e3 := strconv.Atoi(scheme[3])
		if e1 != nil || e2 != nil || e3 != nil || n < 2 || n > 131072 || r < 1 || r > 16 || p2 < 1 || p2 > 4 {
			return false
		}
		got, e = scrypt.Key([]byte(password), []byte(p[1]), n, r, p2, len(want))
		if e != nil {
			return false
		}
	default:
		return false
	}
	return hmac.Equal(got, want)
}

type Action struct {
	Card, CSRF, Nonce string
	Issued            int64
}

func (a *App) action(card, csrf string) string {
	raw, _ := json.Marshal(Action{card, csrf, randomToken(24), time.Now().Unix()})
	p := b64.EncodeToString(raw)
	return p + "." + b64.EncodeToString(mac(a.key, "play:"+p))
}
func (a *App) readAction(value, card, csrf string) (Action, bool) {
	var action Action
	p := strings.Split(value, ".")
	if len(p) != 2 {
		return action, false
	}
	sig, e := b64.DecodeString(p[1])
	if e != nil || !hmac.Equal(sig, mac(a.key, "play:"+p[0])) {
		return action, false
	}
	raw, e := b64.DecodeString(p[0])
	if e != nil || json.Unmarshal(raw, &action) != nil {
		return action, false
	}
	age := time.Now().Unix() - action.Issued
	return action, action.Card == card && equal(action.CSRF, csrf) && action.Nonce != "" && age >= 0 && age <= 120
}

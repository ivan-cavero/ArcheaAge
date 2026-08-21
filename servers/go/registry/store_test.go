package main

import (
	"encoding/json"
	"os"
	"path/filepath"
	"testing"
	"time"
)

func testStore(t *testing.T, contentDir string) *Store {
	t.Helper()
	s := NewStore(defaultVersionSeeds(), map[string]string{"1.2": "dev-secret"}, contentDir)
	base := time.Date(2026, 8, 21, 12, 0, 0, 0, time.UTC)
	s.now = func() time.Time { return base }
	return s
}

func writeManifest(t *testing.T, dir, version, client string, sizes ...int64) {
	t.Helper()
	files := make([]map[string]any, 0, len(sizes))
	for _, sz := range sizes {
		files = append(files, map[string]any{"size": sz})
	}
	body, _ := json.Marshal(map[string]any{"version": version, "client": client, "files": files})
	dir = filepath.Join(dir, "manifests")
	if err := os.MkdirAll(dir, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(dir, version+".json"), body, 0o644); err != nil {
		t.Fatal(err)
	}
}

func TestHeartbeatUpsertAndTTLPrune(t *testing.T) {
	s := testStore(t, t.TempDir())
	hb := HeartbeatRequest{Token: "dev-secret", Version: "1.2", ServerID: "eu-1",
		ServerName: "EU-1", Status: "online", Players: 84, MaxPlayers: 500}

	s.Heartbeat(hb)
	got, known := s.Servers("1.2")
	if !known || len(got) != 1 || got[0].Players != 84 {
		t.Fatalf("expected 1 live server with 84 players, got %+v known=%v", got, known)
	}

	// Advance past the TTL: the entry must be pruned.
	base := s.now()
	s.now = func() time.Time { return base.Add(61 * time.Second) }
	got, _ = s.Servers("1.2")
	if len(got) != 0 {
		t.Fatalf("expected expired server to be pruned, got %+v", got)
	}
}

func TestIsValidToken(t *testing.T) {
	s := testStore(t, t.TempDir())
	if !s.IsValidToken("1.2", "dev-secret") {
		t.Fatal("valid token rejected")
	}
	if s.IsValidToken("1.2", "") || s.IsValidToken("1.2", "wrong") || s.IsValidToken("9.9", "dev-secret") {
		t.Fatal("invalid token accepted")
	}
}

func TestVersionsAggregationFromManifests(t *testing.T) {
	dir := t.TempDir()
	writeManifest(t, dir, "1.2", "1.2.4.0 (r208022)", 100, 200)

	s := testStore(t, dir)
	s.Heartbeat(HeartbeatRequest{Token: "dev-secret", Version: "1.2", ServerID: "eu-1",
		ServerName: "EU-1", Status: "online", Players: 10, MaxPlayers: 100})

	versions := s.Versions()
	var v12 VersionSummary
	for _, v := range versions {
		if v.ID == "1.2" {
			v12 = v
		}
	}
	if v12.Client != "1.2.4.0 (r208022)" || v12.DownloadSize != 300 ||
		v12.Servers != 1 || v12.PlayersOnline != 10 || v12.Status != "live" {
		t.Fatalf("unexpected 1.2 summary: %+v", v12)
	}

	// A seeded version without manifest nor heartbeats stays planned.
	for _, v := range versions {
		if v.ID == "3.5" && (v.Status != "planned" || v.DownloadSize != 0) {
			t.Fatalf("unexpected 3.5 summary: %+v", v)
		}
	}
}

func TestServersUnknownVersionIsNotKnown(t *testing.T) {
	s := testStore(t, t.TempDir())
	if _, known := s.Servers("6.0"); known {
		t.Fatal("version without manifest or heartbeats must not be known")
	}
}

func TestNewsFallbackAndRead(t *testing.T) {
	dir := t.TempDir()
	s := testStore(t, dir)
	if body, ok := s.News(); ok || body != nil {
		t.Fatal("missing news.json should fall back gracefully")
	}
	if err := os.WriteFile(filepath.Join(dir, "news.json"), []byte(`{"items":[1]}`), 0o644); err != nil {
		t.Fatal(err)
	}
	if body, ok := s.News(); !ok || string(body) != `{"items":[1]}` {
		t.Fatalf("news.json not read back: %q %v", body, ok)
	}
}

package main

import (
	"encoding/json"
	"math/rand"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"
)

// heartbeatTTL is how long a server stays visible after its last heartbeat.
// Matches the C# registry (60s).
const heartbeatTTL = 60 * time.Second

// VersionSeed is a known version registered at startup.
type VersionSeed struct {
	ID   string
	Name string
}

// VersionSummary is the GET /versions entry (camelCase, same shape as C#).
type VersionSummary struct {
	ID            string `json:"id"`
	Name          string `json:"name"`
	Client        string `json:"client"`
	Servers       int    `json:"servers"`
	PlayersOnline int    `json:"playersOnline"`
	Status        string `json:"status"` // live | planned
	DownloadSize  int64  `json:"downloadSize"`
}

// ServerInfo is an entry of GET /versions/{v}/servers.
type ServerInfo struct {
	ID            string    `json:"id"`
	Name          string    `json:"name"`
	Version       string    `json:"version"`
	Status        string    `json:"status"`
	Players       int       `json:"players"`
	MaxPlayers    int       `json:"maxPlayers"`
	LastHeartbeat time.Time `json:"lastHeartbeat"`
}

// HeartbeatRequest is the POST /heartbeat body sent by game servers.
type HeartbeatRequest struct {
	Token      string `json:"token"`
	Version    string `json:"version"`
	ServerID   string `json:"serverId"`
	ServerName string `json:"serverName"`
	Status     string `json:"status"`
	Players    int    `json:"players"`
	MaxPlayers int    `json:"maxPlayers"`
}

// manifestFile mirrors the subset of content/manifests/{v}.json we read.
type manifestFile struct {
	Client string `json:"client"`
	Files  []struct {
		Size int64 `json:"size"`
	} `json:"files"`
}

// Store is the in-memory registry state. ponytail: in-memory first,
// MySQL when history/metrics matter (same policy as the C# registry).
type Store struct {
	mu          sync.Mutex
	now         func() time.Time
	contentDir  string // repo content/ dir ("" if not found)
	versions    []VersionSeed
	tokens      map[string]string // version -> heartbeat token
	servers     map[string]ServerInfo
}

// NewStore builds a Store. contentDir may be "" — manifest-dependent
// endpoints then degrade gracefully (planned versions, empty feeds).
func NewStore(versions []VersionSeed, tokens map[string]string, contentDir string) *Store {
	return &Store{
		now:        time.Now,
		contentDir: contentDir,
		versions:   versions,
		tokens:     tokens,
		servers:    make(map[string]ServerInfo),
	}
}

// Versions aggregates heartbeats and manifests into version summaries.
func (s *Store) Versions() []VersionSummary {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.pruneLocked()

	out := make([]VersionSummary, 0, len(s.versions))
	for _, seed := range s.versions {
		count, players := 0, 0
		for _, srv := range s.servers {
			if srv.Version == seed.ID {
				count++
				players += srv.Players
			}
		}
		mf := s.readManifestLocked(seed.ID)
		status := "planned"
		if count > 0 || mf != nil {
			status = "live"
		}
		client, size := "", int64(0)
		if mf != nil {
			client = mf.Client
			for _, f := range mf.Files {
				size += f.Size
			}
		}
		out = append(out, VersionSummary{
			ID: seed.ID, Name: seed.Name, Client: client,
			Servers: count, PlayersOnline: players,
			Status: status, DownloadSize: size,
		})
	}
	return out
}

// Servers lists the live servers of a version. known=false means the caller
// should answer 404 (no heartbeats and no manifest for that version).
func (s *Store) Servers(version string) ([]ServerInfo, bool) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.pruneLocked()

	var out []ServerInfo
	for _, srv := range s.servers {
		if srv.Version == version {
			out = append(out, srv)
		}
	}
	return out, len(out) > 0 || s.manifestExistsLocked(version)
}

// Manifest returns the raw manifest JSON for a version.
func (s *Store) Manifest(version string) ([]byte, bool) {
	s.mu.Lock()
	defer s.mu.Unlock()
	body, err := os.ReadFile(filepath.Join(s.contentDir, "manifests", version+".json"))
	return body, err == nil
}

// News returns the raw news feed JSON.
func (s *Store) News() ([]byte, bool) {
	s.mu.Lock()
	defer s.mu.Unlock()
	body, err := os.ReadFile(filepath.Join(s.contentDir, "news.json"))
	return body, err == nil
}

// IsValidToken reports whether the heartbeat token is valid for the version.
func (s *Store) IsValidToken(version, token string) bool {
	s.mu.Lock()
	defer s.mu.Unlock()
	return token != "" && s.tokens[version] == token
}

// TokenFor exposes the configured token of a version (used by demo mode).
func (s *Store) TokenFor(version string) string {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.tokens[version]
}

// Heartbeat upserts a server report.
func (s *Store) Heartbeat(h HeartbeatRequest) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.servers[h.ServerID] = ServerInfo{
		ID: h.ServerID, Name: h.ServerName, Version: h.Version,
		Status: h.Status, Players: h.Players, MaxPlayers: h.MaxPlayers,
		LastHeartbeat: s.now(),
	}
	s.pruneLocked()
}

func (s *Store) manifestExistsLocked(version string) bool {
	_, err := os.Stat(filepath.Join(s.contentDir, "manifests", version+".json"))
	return err == nil
}

func (s *Store) readManifestLocked(version string) *manifestFile {
	body, err := os.ReadFile(filepath.Join(s.contentDir, "manifests", version+".json"))
	if err != nil {
		return nil
	}
	var mf manifestFile
	if json.Unmarshal(body, &mf) != nil {
		return nil
	}
	return &mf
}

func (s *Store) pruneLocked() {
	cutoff := s.now().Add(-heartbeatTTL)
	for id, srv := range s.servers {
		if srv.LastHeartbeat.Before(cutoff) {
			delete(s.servers, id)
		}
	}
}

// defaultVersionSeeds matches apps/registry/appsettings.json (dev values).
func defaultVersionSeeds() []VersionSeed {
	return []VersionSeed{
		{"1.2", "ArcheAge 1.2 (launch era)"},
		{"3.5", "ArcheAge 3.5 (golden age)"},
		{"6.0", "ArcheAge 6.0"},
		{"7.0", "ArcheAge 7.0"},
		{"8.0", "ArcheAge 8.0 (Kakao)"},
	}
}

// defaultTokens resolves per-version heartbeat tokens: env override
// (REGISTRY_TOKEN_1_2, ...) falling back to the shared dev secret.
func defaultTokens() map[string]string {
	tokens := make(map[string]string, 5)
	for _, v := range defaultVersionSeeds() {
		env := "REGISTRY_TOKEN_" + strings.ReplaceAll(v.ID, ".", "_")
		tokens[v.ID] = envOr(env, "dev-secret")
	}
	return tokens
}

// findContentDir climbs up from the working directory until it finds the
// repo's content/ directory (survives project moves, like the C# fix).
func findContentDir() string {
	dir, err := os.Getwd()
	if err != nil {
		return ""
	}
	for i := 0; i < 10; i++ {
		candidate := filepath.Join(dir, "content", "manifests")
		if st, err := os.Stat(candidate); err == nil && st.IsDir() {
			return filepath.Join(dir, "content")
		}
		parent := filepath.Dir(dir)
		if parent == dir {
			break
		}
		dir = parent
	}
	return ""
}

func newRandom() *rand.Rand { return rand.New(rand.NewSource(time.Now().UnixNano())) }

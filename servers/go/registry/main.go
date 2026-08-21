// Package main is the ArcheaAge Registry written in Go (ADR-001, Slice 0).
//
// It mirrors the C# registry (apps/registry) endpoint-for-endpoint and
// JSON-shape-for-JSON-shape, so the launcher can point at either one:
//
//	GET  /health                     liveness
//	GET  /versions                   version summaries (players aggregated)
//	GET  /versions/{v}/servers       live servers for a version
//	GET  /versions/{v}/manifest      client manifest (content/manifests/{v}.json)
//	GET  /news                       launcher news feed (content/news.json)
//	POST /heartbeat                  game servers report state (per-version token)
//
// Configuration is environment-based (see README.md); defaults match the C#
// appsettings.json development values.
package main

import (
	"encoding/json"
	"flag"
	"log"
	"net/http"
	"os"
	"strconv"
	"strings"
	"time"
)

func main() {
	addr := flag.String("addr", envOr("REGISTRY_ADDR", ":5080"), "listen address")
	flag.Parse()

	store := NewStore(defaultVersionSeeds(), defaultTokens(), findContentDir())

	mux := http.NewServeMux()
	registerRoutes(mux, store)

	if demo, _ := strconv.ParseBool(envOr("REGISTRY_DEMO", "0")); demo {
		startDemoHeartbeats(store)
	}

	log.Printf("ArcheaAge registry (Go) listening on %s", *addr)
	log.Fatal(http.ListenAndServe(*addr, mux))
}

func registerRoutes(mux *http.ServeMux, store *Store) {
	mux.HandleFunc("GET /health", func(w http.ResponseWriter, _ *http.Request) {
		writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
	})

	mux.HandleFunc("GET /versions", func(w http.ResponseWriter, _ *http.Request) {
		writeJSON(w, http.StatusOK, map[string]any{"versions": store.Versions()})
	})

	mux.HandleFunc("GET /versions/{version}/servers", func(w http.ResponseWriter, r *http.Request) {
		servers, known := store.Servers(r.PathValue("version"))
		if !known {
			http.NotFound(w, r)
			return
		}
		writeJSON(w, http.StatusOK, map[string]any{"servers": servers})
	})

	mux.HandleFunc("GET /versions/{version}/manifest", func(w http.ResponseWriter, r *http.Request) {
		body, ok := store.Manifest(r.PathValue("version"))
		if !ok {
			http.NotFound(w, r)
			return
		}
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write(body)
	})

	mux.HandleFunc("GET /news", func(w http.ResponseWriter, _ *http.Request) {
		body, ok := store.News()
		if !ok {
			writeJSON(w, http.StatusOK, map[string]any{"items": []any{}})
			return
		}
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write(body)
	})

	mux.HandleFunc("POST /heartbeat", func(w http.ResponseWriter, r *http.Request) {
		var hb HeartbeatRequest
		if err := json.NewDecoder(r.Body).Decode(&hb); err != nil {
			http.Error(w, "invalid body", http.StatusBadRequest)
			return
		}
		if !store.IsValidToken(hb.Version, hb.Token) {
			http.Error(w, "unauthorized", http.StatusUnauthorized)
			return
		}
		store.Heartbeat(hb)
		writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
	})
}

// startDemoHeartbeats replicates the C# Demo=true mode: fake EU/NA servers
// with fluctuating player counts, for launcher UI development.
func startDemoHeartbeats(store *Store) {
	go func() {
		rnd := newRandom()
		for range time.Tick(10 * time.Second) {
			for _, s := range []struct{ id, name string }{
				{"eu-1", "ArcheaAge EU-1"},
				{"na-1", "ArcheaAge NA-1"},
			} {
				store.Heartbeat(HeartbeatRequest{
					Token:      store.TokenFor("1.2"),
					Version:    "1.2",
					ServerID:   s.id,
					ServerName: s.name,
					Status:     "online",
					Players:    rnd.Intn(180) + 40,
					MaxPlayers: 500,
				})
			}
		}
	}()
}

func writeJSON(w http.ResponseWriter, code int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(code)
	_ = json.NewEncoder(w).Encode(v)
}

func envOr(key, fallback string) string {
	if v := strings.TrimSpace(os.Getenv(key)); v != "" {
		return v
	}
	return fallback
}

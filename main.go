package main

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strings"
)

type Response struct {
	Link string `json:"link"`
}

func getPlayerLink(postID string) (string, error) {

	apiURL := "https://khdiamond.net/wp-admin/admin-ajax.php"

	data := url.Values{}
	data.Set("action", "doo_player_ajax")
	data.Set("post", postID)
	data.Set("nume", "1")
	data.Set("type", "tv")

	req, _ := http.NewRequest("POST", apiURL, strings.NewReader(data.Encode()))

	req.Header.Set("Content-Type", "application/x-www-form-urlencoded")
	req.Header.Set("User-Agent", "Mozilla/5.0")

	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()

	body, _ := io.ReadAll(resp.Body)
	text := string(body)

	start := strings.Index(text, "https://player.khdiamond.net")
	if start == -1 {
		return "", fmt.Errorf("no link found")
	}

	end := strings.Index(text[start:], "\"")
	if end == -1 {
		end = len(text)
	} else {
		end += start
	}

	return text[start:end], nil
}

// API endpoint for Python
func handler(w http.ResponseWriter, r *http.Request) {

	postID := r.URL.Query().Get("post")

	if postID == "" {
		w.WriteHeader(http.StatusBadRequest)
		w.Write([]byte("missing post"))
		return
	}

	link, err := getPlayerLink(postID)
	if err != nil {
		w.WriteHeader(http.StatusInternalServerError)
		w.Write([]byte(err.Error()))
		return
	}

	json.NewEncoder(w).Encode(Response{Link: link})
}

func main() {

	http.HandleFunc("/get", handler)

	fmt.Println("Go server running on :8080")
	http.ListenAndServe(":8080", nil)
}
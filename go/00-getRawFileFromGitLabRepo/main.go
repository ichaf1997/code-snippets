package main

import (
	"errors"
	"fmt"
	"io"
	"net/http"
)

func getRawFileFromRepo(projID string, filePath string, token string, ref string, repoAPI string) ([]byte, error) {
	api := repoAPI + projID + "/repository/files/" + filePath + "/raw?ref=" + ref
	req, err := http.NewRequest("GET", api, nil)
	if err != nil {
		return nil, err
	}
	req.Header.Set("PRIVATE-TOKEN", token)

	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	log.Debug("getRawFileFromRepo using API ", api)

	if resp.Header.Get("X-Gitlab-Blob-Id") == "" {
		msg := fmt.Sprintf("getRawFileFromRepo using API failed, response header %s", httpHeaderString(resp.Header))
		log.Warn(msg)
		return nil, errors.New(msg)
	}
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}

	return body, nil
}

func httpHeaderString(rsp http.Header) string {
	var hts string
	for k, v := range rsp {
		hts = hts + fmt.Sprintf("%s : %s", k, v)
	}
	return hts
}

func main() {

	// rawFile, err := getRawFileFromRepo(xxx)

}

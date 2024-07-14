// Tests for unrestricted HTTP methods/verbs
package tgen

import (
	"encoding/json"

	_ "github.com/OWASP/OFFAT/src/pkg/logging"
	"github.com/OWASP/OFFAT/src/pkg/parser"
	c "github.com/dmdhrumilmistry/fasthttpclient/client"
	"github.com/rs/zerolog/log"
)

// returns a new map with k:parser.DocHttpParams.Name, v:parser.DocHttpParams.Value
func UnrestrictedHttpMethods(docParams []*parser.DocHttpParams, queryParams any, headers any) []*ApiTest {
	var tests []*ApiTest
	testName := "Unrestricted HTTP Methods/Verbs"

	for _, docParam := range docParams {
		bodyMap := ParamsToMap(docParam.BodyParams) // convert it to map[string]interface{}

		// convert it to JSON
		jsonData, err := json.Marshal(bodyMap)
		if err != nil {
			log.Error().Stack().Err(err).Msg("failed to convert bodyMap to JSON")
			jsonData = nil
		}

		// TODO: negate HTTP methods and add it to requests
		// currently below request is only for testing purpose
		request := c.NewRequest(docParam.Url, docParam.HttpMethod, queryParams, headers, jsonData)

		test := ApiTest{
			TestName: testName,
			Request:  request,
			Path:     docParam.Path,
		}
		tests = append(tests, &test)
	}

	return tests
}

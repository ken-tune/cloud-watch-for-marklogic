module namespace content =	"http://marklogic.com/rest-api/resource/content";

import module namespace mock-activity  = "http://marklogic.com/cloud-watch-demo/mock-activity" at "/lib/mock-activity.xqy";

declare function get($context as map:map,$params as map:map) as document-node()*
{
	mock-activity:get-random-documents()
};

declare function put($context as map:map,$params as map:map,$input as document-node()) as document-node()?
{
	xdmp:to-json(map:entry("content",mock-activity:insert-random-documents()))
};
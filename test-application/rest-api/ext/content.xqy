module namespace content =	"http://marklogic.com/rest-api/resource/content";

(:
	This extension is designed to simulate server activity.

	get chooses between $constants:MIN-DOCUMENTS-RETURNED and $constants:MAX-DOCUMENTS-RETURNED documents at random
	put inserts between $constants:MIN-DOCUMENTS-INSERTED and $constants:MAX-DOCUMENTS-INSERTED documents at random

	With probability $constants:CACHE-CLEAR-FREQUENCY the cache is cleared
:)

import module namespace mock-activity  = "http://marklogic.com/cloud-watch-demo/mock-activity" at "/lib/mock-activity.xqy";
import module namespace constants  = "http://marklogic.com/cloud-watch-demo/constants" at "/lib/constants.xqy";
import module namespace util  = "http://marklogic.com/cloud-watch-demo/util" at "/lib/util.xqy";

declare variable $SELECT-PROBABILITY as xs:decimal := 2 div 3;
declare variable $UPDATE-PROBABILITY as xs:decimal := 1 - $SELECT-PROBABILITY;

declare variable $DEBUG := fn:false();

declare function get($context as map:map,$params as map:map) as document-node()*{
	stochastic-cache-clear(),
	mock-activity:get-random-documents(),
	log("GET")

};

declare function put($context as map:map,$params as map:map,$input as document-node()) as document-node()?
{

		xdmp:to-json(map:entry("content",mock-activity:insert-random-documents())),
		log("PUT")
};

declare function stochastic-cache-clear(){
	if(util:true-with-probability(1 div $constants:CLEAR-CACHE-FREQUENCY)) then
	(
		xdmp:expanded-tree-cache-clear(),
		xdmp:compressed-tree-cache-clear(),
		xdmp:list-cache-clear(),
		xdmp:log("Cache Cleared")
	)
	else
	(
		xdmp:log("Not cleared")
	)
};

declare private function log($message as xs:string) as empty-sequence(){
	if($DEBUG) then xdmp:log($message) else ()	
};
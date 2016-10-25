xquery version "1.0-ml";

module namespace mock-activity="http://marklogic.com/cloud-watch-demo/mock-activity";

import module namespace constants = "http://marklogic.com/cloud-watch-demo/constants" at "/lib/constants.xqy";
import module namespace util = "http://marklogic.com/cloud-watch-demo/util" at "/lib/util.xqy";
import module namespace generate-data = "http://marklogic.com/cloud-watch-demo/generate-data" at "/lib/generate-data.xqy";

declare function get-random-documents() as document-node()*{
	let $random-document-count := util:random-between($constants:MIN-DOCUMENTS-RETURNED,$constants:MAX-DOCUMENTS-RETURNED)
	let $document-count := xdmp:estimate(xdmp:directory($constants:DOCS-DIRECTORY))
	return
	for $count in (1 to $random-document-count)
	let $document-index := util:random($document-count)
	let $uri := cts:uris((),(),cts:directory-query($constants:DOCS-DIRECTORY))[$document-index]
	return
	fn:doc($uri)
};

declare function insert-random-documents() as xs:string*{
	let $random-document-count := util:random-between($constants:MIN-DOCUMENTS-INSERTED,$constants:MAX-DOCUMENTS-INSERTED)	
	return
	for $count in (1 to $random-document-count)
	return
	generate-data:insert-random-document()
};
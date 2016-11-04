module namespace sleep =	"http://marklogic.com/rest-api/resource/sleep";

(:import module namespace util  = "http://marklogic.com/cloud-watch-demo/util" at "/lib/util.xqy";:)

declare variable $SLEEP-FIELD-NAME := "period";
declare variable $DEBUG := fn:true();

declare variable $MAX-SLEEP-PERIOD := 10;

declare function get($context as map:map,$params as map:map) as document-node()*{
	let $sleep-period as xs:int := xs:int((map:get($params,$SLEEP-FIELD-NAME),xdmp:random($MAX-SLEEP-PERIOD))[1])
	let $_ := xdmp:sleep($sleep-period * 1000)
	return
	document{"Sleeping for "||$sleep-period}
};



declare private function log($message as xs:string) as empty-sequence(){
	if($DEBUG) then xdmp:log($message) else ()	
};
xquery version "1.0-ml";

module namespace util="http://marklogic.com/cloud-watch-demo/util";

declare function random($max-int) as xs:int{
	xdmp:random($max-int -1) + 1
};

declare function random-between($min-int,$max-int) as xs:int{
	$min-int + xdmp:random($max-int - $min-int)
};
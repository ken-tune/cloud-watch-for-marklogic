xquery version "1.0-ml";

module namespace generate-data="http://marklogic.com/cloud-watch-demo/generate-data";

declare variable $SOURCE-WORDS-FIELD-NAME := "source-words";
declare variable $SOURCE-WORDS-COUNT-FIELD-NAME := "source-words-count";
declare variable $RANDOM-DOCUMENT-MIN-WORD-COUNT := 500;
declare variable $RANDOM-DOCUMENT-MAX-WORD-COUNT := 1000;
declare variable $RANDOM-DOCUMENT-DIRECTORY := "/docs/";
declare variable $RANDOM-DOCUMENT-COLLECTION := "random";
declare variable $OUTPUT-DIRECTORY := "c:\temp\scratch\random-docs\";

declare function insert-random-document(){
  let $url := $RANDOM-DOCUMENT-DIRECTORY||xdmp:md5(xs:string(xdmp:random()))||".xml"
  return
  (
    xdmp:document-insert($url,create-random-document(),xdmp:default-permissions(),$RANDOM-DOCUMENT-COLLECTION),
    $url
  )    
};

declare function create-random-document(){
  let $word-count := $RANDOM-DOCUMENT-MIN-WORD-COUNT + xdmp:random($RANDOM-DOCUMENT-MAX-WORD-COUNT - $RANDOM-DOCUMENT-MIN-WORD-COUNT)
  return
  element root{
    for $count in (1 to $word-count)
    return
    element word{get-random-word()}
   }
};

declare function get-random-word(){
  let $index := xdmp:random(get-source-word-count() - 1) + 1
  return
  xdmp:get-server-field($SOURCE-WORDS-FIELD-NAME)[$index]
};

declare function get-source-word-count() as xs:int{
  let $_ := if(fn:empty(xdmp:get-server-field($SOURCE-WORDS-COUNT-FIELD-NAME))) then
    xdmp:set-server-field($SOURCE-WORDS-COUNT-FIELD-NAME,fn:count(get-source-words()))
  else ()
  return
  xdmp:get-server-field($SOURCE-WORDS-COUNT-FIELD-NAME)
};
  
declare function get-source-words() as xs:string*{
    let $_ := if(fn:empty(xdmp:get-server-field($SOURCE-WORDS-FIELD-NAME))) then 
      xdmp:set-server-field($SOURCE-WORDS-FIELD-NAME,compute-source-words())
    else
    ()
    return
    xdmp:get-server-field($SOURCE-WORDS-FIELD-NAME)
};

declare function compute-source-words(){
  let $source-words := 
  for $word in cts:element-values(xs:QName("available-word"),(),"item-frequency")
  let $frequency := cts:frequency($word)
  return
  for $count in (1 to $frequency)
  return
  $word
  return
  $source-words
};  


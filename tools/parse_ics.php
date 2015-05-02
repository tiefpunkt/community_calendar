<?php
require 'ics-parser/class.iCalReader.php';

class Configuration {
    //Caching settings
    var $cache = "cache/data";
    var $cache_expire = 3600;
}

$config = new Configuration();

$output = "";

if (!isset($_GET['url'])) {
	die('lol, nope.');
}

$urls = [
	"muccc" => "http://api.muc.ccc.de/wiki_kalender.ics",
	"werkbox" => "http://www.werkbox3.de/events.ics",
	"arduino_meetup" => "http://www.meetup.com/Munchen-Arduino-Meetup/events/ical/",
	"mumalab" => "https://www.google.com/calendar/ical/lbd0aa2rlahecp7juvp35hd0k0%40group.calendar.google.com/public/basic.ics"
];

if (!array_key_exists($_GET['url'], $urls)) {
	die("never heard of that cal.");
}

$cache_file = $config->cache . "." . $_GET['url'];

// Try to see if there's some recent cached output available
if (!isset($_GET["refresh"]) && file_exists($cache_file) && (time() < filemtime($cache_file) + $config->cache_expire)) {
	// It is. Let's use that as our output.
	$output = file_get_contents($cache_file);
} else {
	$url = $urls[$_GET['url']];

	$ical   = new ICal($url);
	$events = $ical->events();

	$json_data = [];

	foreach ($events as $event) {
		$start = date("Y-m-d\TH:i:s", $ical->iCalDateToUnixTimestamp($event['DTSTART']));
		$end = date("Y-m-d\TH:i:s", $ical->iCalDateToUnixTimestamp($event['DTEND']));

		$json_event = array("title"=>$event['SUMMARY'], "start"=>$start, "end"=>$end);
		$json_data[] = $json_event;
	}

	$output = json_encode($json_data);

	file_put_contents($cache_file, $output);
}

header('Cache-Control: no-cache, must-revalidate');
header('Expires: Mon, 19 Jul 1997 00:00:00 GMT');
header('Content-type: application/json');

echo $output;

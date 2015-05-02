<?php
class Configuration {
    //Caching settings
    var $cache = "cache/data";
    var $cache_expire = 3600;
}

$config = new Configuration();

$output = "";

if (!isset($_GET["organizer"])) {
    die("lol,nope. No organizer set.");
}

$organizer = $_GET["organizer"];
$cache_file = $config->cache . "." . $organizer;

// Try to see if there's some recent cached output available
if (!isset($_GET["refresh"]) && file_exists($cache_file) && (time() < filemtime($cache_file) + $config->cache_expire)) {
	// It is. Let's use that as our output.
	$output = file_get_contents($cache_file);
} else {

    ini_set('include_path', ini_get('include_path')
            . PATH_SEPARATOR
            . './'
            . PATH_SEPARATOR
            . '../'
            . PATH_SEPARATOR
            . '../../'
            . PATH_SEPARATOR
            . './eventbrite-ics/'
            . PATH_SEPARATOR
    );

    require_once 'classes/EventbriteICS.php';

    $eb_ics = new EventbriteICS();

    $eb_ics->readEventbrite($organizer);

    $json_data = array();

    if ($eb_ics->getEvents()) {
    	# Loop through the feed items and format an event for each
    	foreach ($eb_ics->getEvents()->events as $event) {
    		$start = date("Y-m-d\TH:i:s", strtotime($event->event->start_date));
            $end = date("Y-m-d\TH:i:s", strtotime($event->event->end_date));

    		$json_event = array("title"=>$event->event->title, "start"=>$start, "end"=>$end);
    		$json_data[] = $json_event;
    	}
    }

    $output = json_encode($json_data);

    file_put_contents($cache_file, $output);
}

header('Cache-Control: no-cache, must-revalidate');
header('Expires: Mon, 19 Jul 1997 00:00:00 GMT');
header('Content-type: application/json');

echo $output;

function dateString(d) {
	return "" + d.getFullYear() + "-" + d.getMonth() + "-" + d.getDay();
}


$(document).ready(function() {
	// load available calendars via AJAX
	$.getJSON("data/_sources.json", function(data) {

		// render calendar
		$('#calendar').fullCalendar({
			firstDay: 1, // week starts on a Monday
			header: {
				left: 'prev,next today',
				center: 'title',
				right: 'month,agendaWeek,agendaDay'
			},
			defaultView: 'month',
			eventLimit: true, // allow "more" link when too many events
			eventSources: data, //  Event sources from AJAX call

			// Open sidebar when clicking on an event
			eventClick: function(calEvent, jsEvent, view) {
				$("#sidebar h1").html(calEvent.title);

				if (calEvent.description) {
					$("#sidebar #description").html(calEvent.description.replace(/(?:\r\n|\r|\n)/g, '<br>'));
				} else {
					$("#sidebar #description").html("");
				};

				$("#sidebar #dtstart").html(calEvent.start.format("YYYY-MM-DD HH:mm"));

				if (calEvent.end) {
					$("#sidebar #dtend").html(calEvent.end.format("YYYY-MM-DD HH:mm"));
				} else {
					$("#sidebar #dtend").html(calEvent.start.format("YYYY-MM-DD HH:mm"));
				}

				if (calEvent.location) {
					$("#sidebar #location").html(calEvent.location);
					$("#sidebar #location_wrapper").show();
				} else {
					$("#sidebar #location").html(calEvent.location);
					$("#sidebar #location_wrapper").hide();
				}

				// Slide in from the right.
				$("#sidebar").animate({"right":"0"},"fast");
			}
		});

		// Render calendar legend
		var legend = [];
		$.each( data, function( key, val ) {
			legend.push("<li><span class=\"legend_box\" style=\"background: " + val["color"] + ";\"></span> " + val["title"] + "</li>")
		});
		$("#legend").html(legend.join(""));
	});

	// Attach close action to x in top right corner of sidebar
	$("#sidebar .close_button").click(function(event) {
		event.preventDefault();
		//$("#sidebar").hide("fast");
		$("#sidebar").animate({"right":"-410px"},"fast");
	});
});

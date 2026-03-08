function dateString(d) {
    return "" + d.getFullYear() + "-" + d.getMonth() + "-" + d.getDay();
}

$(document).ready(function () {
    // load available calendars via AJAX
    $.getJSON("data/_sources.json", function (data) {

        var calendarEl = document.getElementById('calendar');
        var calendar = new FullCalendar.Calendar(calendarEl, {
            initialView: 'dayGridMonth',
            headerToolbar: {
                left: 'prev,next today',
                center: 'title',
                right: 'dayGridMonth,timeGridWeek,timeGridDay'
            },
            eventSources: data, //  Event sources from AJAX call
            firstDay: 1, // week starts on a Monday
            locale: 'de', // German locale
            eventTimeFormat: {
                hour: 'numeric',
                minute: '2-digit',
                meridiem: false
            },
            eventClick: function (info) {
                info.jsEvent.preventDefault();
                $("#sidebar h1").html(info.event.title);

                if (info.event.extendedProps.description) {
                    $("#sidebar #description").html(info.event.extendedProps.description.replace(/(?:\r\n|\r|\n)/g, '<br>'));
                } else {
                    $("#sidebar #description").html("");
                };
                var dtformat = new Intl.DateTimeFormat('de-DE', {
                    dateStyle: "medium",
                    timeStyle: "short"
                });
                $("#sidebar #dtstart").html(dtformat.format(info.event.start));

                if (info.event.end) {
                    $("#sidebar #dtend").html(dtformat.format(info.event.end));
                } else {
                    $("#sidebar #dtend").html(dtformat.format(info.event.start));
                }

                if (info.event.extendedProps.location) {
                    $("#sidebar #location").html(info.event.extendedProps.location);
                    $("#sidebar #location_wrapper").show();
                } else {
                    $("#sidebar #location").html("");
                    $("#sidebar #location_wrapper").hide();
                }

                // Slide in from the right.
                $("#sidebar").animate({ "right": "0" }, "fast");
            }
        });
        calendar.render();

        // Render calendar legend
        var legend = [];
        $.each(data, function (key, val) {
            legend.push("<li><span class=\"legend_box\" style=\"background: " + val["color"] + ";\"></span> " + val["title"] + "</li>")
        });
        $("#legend").html(legend.join(""));
    });

    // Attach close action to x in top right corner of sidebar
    $("#sidebar .close_button").click(function (event) {
        event.preventDefault();
        //$("#sidebar").hide("fast");
        $("#sidebar").animate({ "right": "-410px" }, "fast");
    });
});

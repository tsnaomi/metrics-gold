(function() {
    function generage_csv() {
        $('.csv').on('click', function(event) {
            var $csv = $(this);
            var title = $csv.attr('id');
            var csrf_token = $csv.attr('name');
            var csv_view = '/csv/' + title;

            // display loading overlay
            var $html = $('html');
            var $overlay = $('<div class="overlay"><div class="loading"></div></div>');
            $html.append($overlay);

            // alert user of long wait time
            alert('Pardon the wait! This csv will take a few minutes to generate. Please stay on this page until the file is downloaded.');

            $.post(csv_view, { _csrf_token: csrf_token }, function() {
                // yea!
                window.location.href = '/static/csv/' + title + '.csv';
            }).fail(function(jqXHR, textStatus, errorThrown) {
                // nay!
                alert('Sorry, something went awry!\n\nError: ' + (errorThrown || 'Unknown'));
            }).always(function() {
                // remove loading overlay
                $('.overlay').remove();
            });
        });
    }
    generage_csv();
})(); 


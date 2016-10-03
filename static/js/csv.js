(function() {

    function generage_csv() {
        $('.download').on('click', function(event) {
            var $download = $(this);
            var title = $download.attr('id');
            var csrf_token = $download.attr('name');
            var csv_view = '/generate-csv/' + title;

            // change cursors to spinner
            $download.addClass('wait');
            document.body.style.cursor = 'wait';


            $.post(csv_view, { _csrf_token: csrf_token }, function() {
                // download csv file
                window.location = '/static/csv/' + title + '.csv';
            }).fail(function() {
                // notify user that the csv file cannot be generated
                alert('Something went awry. Please tell Naomi.');
            }).always(function() {
                // restore cursors
                document.body.style.cursor = 'default';
                $download.removeClass('wait');
            });

        });
    }

    generage_csv();

})(); 


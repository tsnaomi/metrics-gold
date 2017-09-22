(function() {
    function generage_csv() {
        var $text = $('.text');
        var title = $text.attr('id');
        var csrf_token = $text.attr('name');
        var csv_view = '/csv/' + title;

        // get the csv via ajax
        $.post(csv_view, { _csrf_token: csrf_token }, function() {
            // yea!
            window.location.href = '/static/csv/' + title + '.csv';
            $text.html('The csv <strong>' + title + '</strong> has successfully download.')
        }).fail(function(jqXHR, textStatus, errorThrown) {
            // nay!
            alert('Sorry, something went awry!\n\nError: ' + (errorThrown || 'Unknown'));
            $text.html('The csv <strong>' + title + '</strong> has failed to download.')
        }).always(function() {
            // remove loading overlay
            $('.loading').remove();
        });
    }
    generage_csv();
})(); 
(function() {
    function generage_csv() {
        var $text = $('.text');
        var $title = $('title');
        var file = $text.attr('id');
        var csrf_token = $text.attr('name');
        var csv_view = '/csv/' + file;
        console.log('Downloading...');

        // get the csv via ajax
        $.post(csv_view, { _csrf_token: csrf_token }, function() {
            // yea!
            console.log('Success!');
            window.location.href = '/static/csv/' + file + '.csv';
            $text.html('The csv <strong>' + file + '</strong> has successfully downloaded.');
            $title.text('Download complete!');
        }).fail(function(jqXHR, textStatus, errorThrown) {
            // nay!
            console.log('Failure!');
            alert('Sorry, something went awry!\n\nError: ' + (errorThrown || 'Unknown'));
            $text.html('The csv <strong>' + file + '</strong> has failed to download.');
            $title.text('Download failed.');
        }).always(function() {
            console.log('Removing spinner.');
            // remove loading overlay
            $('.loading').remove();
        });
    }
    generage_csv();
})(); 
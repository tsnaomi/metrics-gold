(function() {
    function generage_csv() {
        var $title = $('title');
        var $dir = $('.dir');
        var $text = $('.text');
        var dir = $dir.attr('id');
        var file = $text.attr('id');
        var csrf_token = $text.attr('name');
        var csv_view = '/csv/' + file;

        console.log($dir, dir)

        // get the csv via ajax
        $.post(csv_view, { _csrf_token: csrf_token }, function() {
            // yea!
            $('.loading').remove(); // remove loading overlay
            window.location.href = '/static/csv/' + dir + file + '.csv';
            $text.html('The csv <strong>' + file + '</strong> has successfully downloaded.');
            $title.text('Download complete!');
        }).fail(function(jqXHR, textStatus, errorThrown) {
            // nay!
            $('.loading').remove(); // remove loading overlay
            $title.text('Download failed');
            $text.html('The csv <strong>' + file + '</strong> has failed to download.<div class="div20"></div>Error:&nbsp;&nbsp;' + (errorThrown || 'Unknown'));
            setTimeout(function() {
                alert('Sorry, something went awry!');
            }, 0);
        });
    }
    generage_csv();
})();
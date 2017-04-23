(function() {

    function generage_csv() {
        $('.mail').on('click', function(event) {
            var $div = $('.flash-alert');
            var $mail = $(this);
            var title = $mail.attr('id');
            var csrf_token = $mail.attr('name');
            var csv_view = '/mail-csv/' + title;
            var msg;

            // change cursors to spinner
            $mail.addClass('wait');
            document.body.style.cursor = 'wait';

            $.post(csv_view, { _csrf_token: csrf_token }, function() {
                // yea!
                msg = 'Please check your email in a few minutes!';

            }).fail(function() {
                // nay!
                msg = 'Sorry! Something weny awry.';

            }).always(function() {
                alert(msg);

                // restore cursors
                document.body.style.cursor = 'default';
                $mail.removeClass('wait');
            });
        });
    }

    generage_csv();

})(); 


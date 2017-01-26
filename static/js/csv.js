(function() {

    function generage_csv() {
        $('.mail').on('click', function(event) {
            var $mail = $(this);
            var title = $mail.attr('id');
            var csrf_token = $mail.attr('name');
            var csv_view = '/mail-csv/' + title;
            var msg = "<div class='mail-alert'>&nbsp;&nbsp;&nbsp;&nbsp;";

            // change cursors to spinner
            $mail.addClass('wait');
            document.body.style.cursor = 'wait';

            $.post(csv_view, { _csrf_token: csrf_token }, function() {
                // yay!!
                msg += 'Please check your email in a few minutes!</div>';
                $mail.html(msg);
            }).fail(function() {
                // uh-oh!
                msg += 'Sorry! Something weny awry. Please tell Naomi.</div>';
                $mail.html(msg);
            }).always(function() {
                // restore cursors
                document.body.style.cursor = 'default';
                $mail.removeClass('wait');
                // display message
                $('.mail-alert').fadeIn();
                // hide and remove message
                setTimeout(function() {
                    $('.mail-alert').fadeOut(1200, function() {
                        $(this).remove();
                    });
                }, 2000);
            });
        });
    }

    generage_csv();

})(); 


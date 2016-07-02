(function() {

    function showSpinnerOnWelcomeSubmit() {
        $('input[value="Sign Up"]').on('click', function() {
            // hide flash messages
            $('.flash').addClass('hide');

            // show spinner
            $('.spinner').removeClass('hide');
        });
    }

    showSpinnerOnWelcomeSubmit();

})(); 
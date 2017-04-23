(function() {

    function precaution() {
        $('#username').on('input', function() {
            var username = $(this).val();
            var $statement = $('#statement');
            var statement = username + '\'s annotations';

            if (username) {
                $statement.text(statement);
            } else {
                $statement.text('...');
            }
        });

        $('#precaution').on('keypress, keyup', function() {
            statement1 = $(this).val();
            statement2 = 'I hereby delete ' + $('#statement').text();
            
            if (statement1 === statement2) {
                $('button').prop('disabled', false);
            } else {
                $('button').prop('disabled', true);
            }
        });
    }

    precaution();

})(); 
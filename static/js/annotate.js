(function() {

    // fade out flash elements
    function fadeFlash() {
        window.setTimeout(function() { $('.flash').fadeOut(400); }, 400);
    }

    // deselect checked radio buttons on click
    function deselectRadio() {
        $(':checked').addClass('selected');

        $(':checked').on('load', function() {
            $(this).addClass('selected');
        });

        $('input:radio').on('click', function(event) {
            var $input = $(this);
            var thisName = $input.prop('name');
            var selector;

            if ($input.is('.selected')) {
                $input.prop('checked', false).removeClass('selected');
                selector = 'input[value=0][name=' + thisName + ']';
                $(selector).prop('checked', true).addClass('selected');
            } else {
                selector = 'input:radio[name=' + thisName + '].selected';
                $(selector).removeClass('selected');
                $input.addClass('selected');
            }
        });
    }

    fadeFlash();
    deselectRadio();

})(); 
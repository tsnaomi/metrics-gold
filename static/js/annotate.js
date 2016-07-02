(function() {

    // fade out flash elements
    function fadeFlash() {
        window.setTimeout(function() { $('.flash').fadeOut(400); }, 400);
    }

    // deselect checked radio buttons on click
    function deselectRadio() {
        $(':checked').on('load', function() {
            $(this).addClass('selected');
        });

        $(':checked').addClass('selected');

        $('input:radio').on('click', function(event) {
            var $input = $(this);
            var selector;

            if ($input.is('.selected')) {
                $input.prop('checked', false).removeClass('selected');
                selector = 'input[value="0"][name="' + $input.prop('name') + '"].theone';
                $(selector).prop('checked', true);
            } else {
                selector = 'input:radio[name="' + $input.prop('name') + '"].theone';
                $(selector).removeClass('selected');
                $input.addClass('selected');
            }
        });
    }

    fadeFlash();
    deselectRadio();

})(); 
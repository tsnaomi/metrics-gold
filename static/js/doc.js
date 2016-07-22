(function() {

    function scroll() {
        $(document).ready(function () {
            var buffer = 240;
            var $inProgress = $('.in-progress');
            var $unannotated = $('.unannotated');

            if ($inProgress[0]) {
                $('body').animate(
                    { scrollTop: $inProgress.offset().top - buffer },
                    'slow'
                );
            } else if ($unannotated[0]) {
                $('body').animate(
                    { scrollTop: $unannotated.offset().top - buffer },
                    'slow'
                );
            }
        });
    }

    scroll();

})(); 
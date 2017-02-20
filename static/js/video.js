(function() {
    var $IFRAME = $('iframe');
    var URL = $IFRAME.attr('src');

    // reload and play video slice
    function playVideoSlice() {
        $('#play-video').on('click', function(event) {
            event.preventDefault();
            $IFRAME.attr('src', URL + '&autoplay=1');
        });
    }

    playVideoSlice();

})(); 
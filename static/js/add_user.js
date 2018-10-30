(function() {

    function toggleCourses() {
        $('input[type=radio][name=role').change(function() {
            var $student = $('#student-radio');
            var $courses = $('#courses');
            var $select = $('select');

            if ($student.is(':checked')) {
                $courses.show();
                $select.prop('selectedIndex', 0);
            } else {
                $courses.hide();
                $select.prop('selectedIndex', -1);
            }
        });
    }

    toggleCourses();

})(); 
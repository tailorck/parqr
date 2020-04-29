$(document).ready(function () {
  $('#dtBasicExample').DataTable();
  $('.dataTables_length').addClass('bs-select');
});


$(document).ready(function(){
  $('#dtBasicExample tbody').on("click", 'tr',  function(){
    var toggleSwitchId = $(this).find('input')[0].id;
    var course_id = $(this).find('td:first-child').text();
    var status_span = $(this).find('td:nth-child(5)').find('span');
    var toggleStatus = $('#' + toggleSwitchId).prop('checked');

    $('#'+toggleSwitchId).on("click", function() {
      $('#' + toggleSwitchId).prop('disabled', true);
      if(toggleStatus === true) {
        $.ajax({
          url: "https://aws.parqr.io/dev/courses/" + course_id + "/active",
          type: "DELETE",
          dataType: "json",
          contentType: 'application/json',
          success: function (result) {
            status_span.removeClass('badge badge-success').addClass('badge badge-primary');
            status_span.text('In progress');
            window.location.reload();
          },
          error: function (error) {
            window.location.reload();
          }
        });

      } else {
        $.ajax({
          url: "https://aws.parqr.io/dev/courses/" + course_id + "/active",
          type: "POST",
          dataType: "json",
          contentType: 'application/json',
          success: function (result) {
            status_span.removeClass('badge badge-danger').addClass('badge badge-primary');
            status_span.text('In progress');
            window.location.reload();
          },
          error: function (error) {
            status_span.removeClass('badge badge-danger').addClass('badge badge-primary');
            status_span.text('In progress');
            window.location.reload();
          }
        });
      }
    });
  });
});

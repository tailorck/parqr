$(document).ready(function () {
  $('#dtBasicExample').DataTable();
  $('.dataTables_length').addClass('bs-select');
});

function getCookie(cname) {
  var name = cname + "=";
  var decodedCookie = decodeURIComponent(document.cookie);
  var ca = decodedCookie.split(';');
  for(var i = 0; i <ca.length; i++) {
    var c = ca[i];
    while (c.charAt(0) == ' ') {
      c = c.substring(1);
    }
    if (c.indexOf(name) == 0) {
      return c.substring(name.length, c.length);
    }
  }
  return "";
}


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
          url: "https://aws.parqr.io/prod/courses/" + course_id + "/active",
          headers: {
            "id_token": getCookie("id_token")
          },
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
          url: "https://aws.parqr.io/prod/courses/" + course_id + "/active",
          headers: {
            "id_token": getCookie("id_token")
          },
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

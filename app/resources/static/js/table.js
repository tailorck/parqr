$(document).ready(function () {
$('#dtBasicExample').DataTable();
$('.dataTables_length').addClass('bs-select');
});


$(document).ready(function(){
    $('#dtBasicExample tbody').on("click", 'tr',  function(){
    	var toggleId = $(this).find('input')[0].id;
        var valueOfTd = $(this).find('td:first-child').text();
        var status = $(this).find('td:nth-child(5)').find('span');
        var toggleStatus = $('#' + toggleId).prop('checked');

        console.log(toggleId);
        console.log(valueOfTd); 
        console.log(status);
        console.log(toggleStatus);


        $('#customSwitch0').on("click", function() {
    		$('#' + toggleId).prop('disabled', true);
        	if(toggleStatus === true) {

        		$.ajax({
		        	url: "https://aws.parqr.io/dev/courses/" + valueOfTd + "/active",
		        	type: "DELETE",
		        	dataType: "json",
		        	contentType: 'application/json',
		        	success: function (result) {
		        		status.removeClass('badge badge-success').addClass('badge badge-primary');
        				status.text('In progress');
		        		window.location.reload();
		        		console.log(result);
		        	},
		        	error: function (error) {
		        		window.location.reload();
		        		console.log(error);
		        	}
		        });

        	} else {

        		$.ajax({
		        	url: "https://aws.parqr.io/dev/courses/" + valueOfTd + "/active",
		        	type: "POST",
		        	dataType: "json",
		        	contentType: 'application/json',
		        	success: function (result) {
		        		status.removeClass('badge badge-danger').addClass('badge badge-primary');
        				status.text('In progress');
		        		window.location.reload();
		        		console.log(result);
		        	},
		        	error: function (error) {
		        		status.removeClass('badge badge-danger').addClass('badge badge-primary');
        				status.text('In progress');
		        		window.location.reload();
		        		console.log(error);
		        	}
		        });

        	}


        });


        
    });
});




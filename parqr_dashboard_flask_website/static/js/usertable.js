$(document).ready(function () {
$('#dtBasicExample').DataTable();
$('.dataTables_length').addClass('bs-select');
});


$(document).ready(function(){
    $('#dtBasicExample tbody').on("mouseenter", 'tr',  function(){
    	var username = $(this).find('td:nth-child(2)').text();
        var button = $(this).find('td:nth-child(3)').find('button');
        button.on("click", function(){

        	$.ajax({
    				url: '/delete',
		        	type: "POST",
		        	data: {deleteUserName : username},
		        	success: function (result) {
		        		window.location.reload();
		        		console.log(result);
		        	},
		        	error: function (error) {
		        		// window.location.reload();
		        		console.log(error);
		        	}
		        });
        });
    });
});




console.log('content script loaded')

collapsible_container = `
	<div class="container">
  	<div class="panel-group">
    	<div class="panel panel-default">
				<div id="collapse" class="panel-collapse collapse">
					<div class="panel-body">Sample Panel Body</div>
				</div>
    	</div>
  	</div>
	</div>	
	`;

suggestions_html = `
	<div id="suggestions">
		<b>Questions that may already have your answer:</b>
		<br>
	</div>
	`;

function newButtonClick(e) {
	/*
	document.getElementsByClassName("right_section")[3].innerHTML += collapsible_container;
	$("#collapse").collapse("show");
	*/

	setTimeout(function() {
		body_iframe = document.getElementById('rich_old_new_post_ifr').contentWindow;
		selected_tags = document.getElementsByClassName('right_section')[2]
			.getElementsByClassName('selected');

		var tag_texts = [];
		for (var i=0, len = selected_tags.length; i < len; i++) {
			tag_texts.push(selected_tags[i].innerText);
		};

		var words = [];
		words.push(document.getElementById('post_summary').value);
		words.push(body_iframe.document.getElementsByTagName('p')[0].innerText);
		words.push(tag_texts.join(' '));

		var url = window.location.href;
		var cid = url.substring(url.length-14);	

		console.log('Sending: ' + words.join(' '))
		chrome.runtime.sendMessage({words: words.join(' '), cid: cid}, function(response) {
			response = JSON.parse(response);
			document.getElementsByClassName("right_section")[3].innerHTML += suggestions_html;
			suggestions_tag = document.getElementById("suggestions");
			sorted_scores = Object.keys(response).sort().reverse();
			for (i = 0; i < sorted_scores.length; i++) {
				key = sorted_scores[i];
				pid = response[key]["pid"];
				url = window.location.href + "?cid=" + pid;

				rounded_score = Math.round(parseFloat(key)*1000)/1000;
				innerText = rounded_score + ": " + response[key]["subject"];
				suggestions_tag.innerHTML += '<a href=' + url + '>' + innerText + '</a><br>';
			}
		});
	}, 30000);
}

document.getElementById('new_post_button').addEventListener('click', newButtonClick);

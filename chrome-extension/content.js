recommendations_html = `
	<div id="recommendations">
		<b>Questions that may already have your answer:</b>
		<div id="r_links">
		</div>
	</div>
	`;

SIGNIFICANT_DIFF = 5;

function newButtonClick(e) {
	//document.getElementsByClassName("right_section")[3].innerHTML += collapsible_container;
	//$("#collapse").collapse("show");

	var curr_length = 0;
	setInterval(function() {
		curr_length = parsePiazzaText(curr_length);
	}, 10000);
}

function parsePiazzaText(curr_length) {
	var cid = getCourseId();
	var words = getWords();
	var new_length = words.length;

	if (new_length > 0 && Math.abs(new_length - curr_length) > SIGNIFICANT_DIFF) {
		console.log('Sending: ' + words);
		chrome.runtime.sendMessage({words: words, cid: cid}, function(response) {
			if (!response) {
				return curr_length;
			}
			response = JSON.parse(response);
			
			// Insert the recommendation template if it is not already there
			if (document.getElementById("recommendations") == null) {
				document.getElementsByClassName("right_section")[3].innerHTML += recommendations_html;
			}

			// Grab a handle to the links div and remove the previous links
			var r_links = document.getElementById("r_links");
			r_links.innerHTML = "";
			
			var sorted_scores = Object.keys(response).sort().reverse();
			for (i = 0; i < sorted_scores.length; i++) {
				var score = sorted_scores[i];
				var pid = response[score]["pid"];
				var url = window.location.href + "?cid=" + pid;

				// var rounded_score = Math.round(parseFloat(score)*1000)/1000;
				var innerText = "@{0}:\t{1}".format(pid, response[score]["subject"]);
				r_links.innerHTML += '<a href={0} target="_blank">{1}</a><br>'.format(url, innerText);
			}
		});
		return new_length;
	}
	return curr_length;	
}

function getCourseId() {
	var url = window.location.href;
	var cidRegExp = /piazza\.com\/class\/([a-z1-9]+)/;
	var match = cidRegExp.exec(url);
	return match[1];
}

function getTags() {
	var selected_tags = document.getElementsByClassName('right_section')[2]
		.getElementsByClassName('selected');

	var tag_texts = [];
	for(var i=0; i < selected_tags.length; i++) {
		tag_texts.push(selected_tags[i].innerText);
	}

	return tag_texts.join(' ');
}

function getWords() {
	var body_iframe = document.getElementById('rich_old_new_post_ifr').contentWindow;

	var tag_texts = getTags();
	var word_list = [];

	var summary = document.getElementById('post_summary').value;
	var body = body_iframe.document.getElementsByTagName('p')[0].innerText;

	if (summary.length > 0) {
		word_list.push(summary);
	}

	if (body.length > 0 && body != '\n') {
		word_list.push(body);
	}

	if (tag_texts.length > 0) {
		word_list.push(tag_texts);
	}

	return word_list.join(' ');
}

// First, checks if it isn't implemented yet.
if (!String.prototype.format) {
	// Create a String function to mimic sprintf
  String.prototype.format = function() {
    var args = arguments;
    return this.replace(/{(\d+)}/g, function(match, number) { 
      return typeof args[number] != 'undefined'
        ? args[number]
        : match
      ;
    });
  };
}

document.getElementById('new_post_button').addEventListener('click', newButtonClick);

console.log('content script loaded')

/*
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
*/

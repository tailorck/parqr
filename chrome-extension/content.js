recommendations_html = `
	<div id="recommendations">
		<b>These posts may already have your answer:</b>
		<ul id="rec_link_list">
		</ul>
	</div>
	`;


SIGNIFICANT_DIFF = 5;

$(document).ready(function() {
	$("#new_post_button").click(newButtonClick);
});

console.log('content script loaded')

function newButtonClick(e) {
	var curr_length = 0;
	setInterval(function() {
		curr_length = parsePiazzaText(curr_length);
	}, 1000);
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
			if ($("#recommendations").length == 0) {
				$(".right_section")[3].innerHTML += recommendations_html;
			}

			// Grab a handle to the links div and remove the previous links
			var $rec_link_list = $("#rec_link_list") 
			$rec_link_list[0].innerHTML = "";
		
			// Insert recommendations into template in order of best score
			var sorted_scores = Object.keys(response).sort().reverse();
			for (i = 0; i < sorted_scores.length; i++) {
				// Extract pertinent information from response json
				var score = sorted_scores[i];
				var pid = response[score]["pid"];
				var subject = response[score]["subject"];
				var dest = window.location.href + "?cid=" + pid;
				var s_answer_exists = response[score]["s_answer"];
				var i_answer_exists = response[score]["i_answer"];

				// Create a rounded box with the pid of the suggestion
				var $pid_link = $('<button>').text('@' + pid).addClass("box");
				if (s_answer_exists) {
					$pid_link.addClass("box-yellow");
				} else if (i_answer_exists) {
					$pid_link.addClass("box-green");
				} else {
					$pid_link.addClass("box-blend");
				}

				// Create a link with the subject of the suggestions
				var link_string = '<a href="{0}" target="_blank" class="rec_link"></a>'.format(dest);
				var $subject_link = $(link_string).html(subject);

				var pid_html = $pid_link[0].outerHTML;
				var subject_html = $subject_link[0].outerHTML;
				$rec_link_list.append($('<li>').html('{0}{1}'.format(pid_html, subject_html)));
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
	var selected_tags = $('.right_section')[2]
		.getElementsByClassName('selected');

	var tag_texts = [];
	for(var i=0; i < selected_tags.length; i++) {
		tag_texts.push(selected_tags[i].innerText);
	}

	return tag_texts.join(' ');
}

function getWords() {
	var body_iframe = $('#rich_old_new_post_ifr')[0].contentWindow;

	var tag_texts = getTags();
	var word_list = [];

	var summary = $('#post_summary').val();
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

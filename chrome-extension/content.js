recommendations_html = `
	<div id="parqr-recommendations">
		<b>These posts may already have your answer:</b>
		<ul id="rec_link_list">
		</ul>
	</div>`


$(document).ready(function() {
	$("#new_post_button").click(newButtonClick);
});

var DEBOUNCE_IN_MS = 300

function newButtonClick(e) {
	$("#post_summary").parent().append(recommendations_html)
	$('#post_summary').keyup(debounce(DEBOUNCE_IN_MS, parsePiazzaText))
}

function parsePiazzaText() {
	var cid = getCourseId();
	var words = getWords();

	// If works is empty, don't send anything back but clear the list
	if (!words) {
		clearSuggestions();
	}
	else {
		console.log('Sending: ' + words);
		chrome.runtime.sendMessage({words: words, cid: cid}, function(response) {
			if (!response) {
				return curr_length;
			}
			response = JSON.parse(response);
			clearSuggestions()
			
			// Grab a handle to the links div and remove the previous links
			var $rec_link_list = $("#rec_link_list") 
		
			// Insert recommendations into template in order of best score
			var sorted_scores = Object.keys(response).sort().reverse();
			for (i = 0; i < sorted_scores.length; i++) {
				// Extract pertinent information from response json
				var score = sorted_scores[i];
				var pid = response[score]["pid"];
				var subject = response[score]["subject"];
				var dest = window.location.href.split('?')[0] + "?cid=" + pid;
				var s_answer_exists = response[score]["s_answer"];
				var i_answer_exists = response[score]["i_answer"];

				// Create a rounded box with the pid of the suggestion
				var $pid_link = $('<button>').text('@' + pid).addClass("box");
				if (i_answer_exists) {
					$pid_link.addClass("box-yellow");
				} else if (s_answer_exists) {
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
	}
}

function clearSuggestions() {
	$("#rec_link_list").empty()
	
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

// Given a delay function and a callback, debounces a function for that amount of time.
function debounce(delay, callback) {
	var timeout;
	return function() {
		console.log("debounce")
		clearTimeout(timeout)
		timeout = setTimeout(callback, delay)
	}
}
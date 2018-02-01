var browser;

try {
    // For Chrome
    browser = chrome
} catch (error) {

    try {
        // For Firefox
        browser = browser
    } catch(error) {

    }
}

recommendations_html = `
	<div id="parqr-recommendations">
		<span id="search-results-header"></span>
		<ul id="rec_link_list">
		</ul>
	</div>`

searchResultsHeaderHtml = "<span><b>These posts may already have your answer:</b><span>"

$(document).ready(function() {
	$("#new_post_button").click(newButtonClick);
});

var DEBOUNCE_IN_MS = 300

function newButtonClick(e) {
	sendEvent('newPost', {cid: getCourseId()})
	$("#post_summary").parent().append(recommendations_html)
	$('#post_summary').keyup(debounce(DEBOUNCE_IN_MS, parsePiazzaText))

	// Add listener to the rich text editor
	// .contents().find("#tinymce") is necessary in order to find elements within the #rich_old_new_post_ifr
	// iframe. They cannot be referenced directly
	$("#rich_old_new_post_ifr").contents().find("#tinymce").keyup(debounce(DEBOUNCE_IN_MS, parsePiazzaText))

	// Add listener to the plain text editor
	$("#rich_old_new_post").keyup(debounce(DEBOUNCE_IN_MS, parsePiazzaText))

	// Parse text when a tag is clicked
	$(".tag").click(debounce(DEBOUNCE_IN_MS, parsePiazzaText))

	// Send an event when the "submit post" button is clicked
	$("#post_button").click(function() {
		var eventData = getWords()
		eventData.cid = getCourseId() 
		sendEvent('postSubmitted', eventData)
	})
}

var request_counter = 0
var latest_processed_req = -1

var suggestions = []

function parsePiazzaText() {
	var cid = getCourseId();
	var words = getWords();

	// If works is empty, don't send anything back but clear the list
	if (!words) {
		removeSearchResultsHeader()
		clearSuggestions();
	}
	else {
		var req_id = request_counter
		request_counter += 1
		browser.runtime.sendMessage({words: words, cid: cid, type: 'query'}, function(response) {
			if (req_id < latest_processed_req) {
				return
			} 
			suggestions = []

			latest_processed_req = req_id

			if (!response) {
				removeSearchResultsHeader()
				return
			}

			clearSuggestions()

			// If there are no recomendations, return
			if (Object.keys(response).length === 0){
				removeSearchResultsHeader()
				return
			}

			// Grab a handle to the links div and remove the previous links
			var $rec_link_list = $("#rec_link_list")
		
			// Insert recommendations into template in order of best score
			var sorted_scores = Object.keys(response).sort().reverse();

			insertSearchResultsHeader()
			// Add all of the scores to the recomendations lists
			for (i = 0; i < sorted_scores.length; i++) {
				// Extract pertinent information from response json
				var score = sorted_scores[i];
				var pid = response[score]["pid"];
				var subject = response[score]["subject"];
				var dest = window.location.href.split('?')[0] + "?cid=" + pid;
				var s_answer_exists = response[score]["s_answer"];
				var i_answer_exists = response[score]["i_answer"];

				suggestions.push({
					pid: pid,
					has_s_answer: s_answer_exists,
					has_i_answer: i_answer_exists,
					subject: subject,
					score: score,
				})

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

				$subject_link.click(function() {
					console.log("CLICKED IT")
				})

				var pid_html = $pid_link[0].outerHTML;
				var subject_html = $subject_link[0].outerHTML;

				$rec_link_list.append($('<li class="parqr-suggestion">').html('{0}{1}'.format(pid_html, subject_html)));
			}

			$rec_link_list.on('click', '.rec_link', function(ev) {
				var target = ev.target
				var li = $(target).parent()[0]
				link_index = $('.parqr-suggestion').index(li)
				eventData = JSON.parse(JSON.stringify(suggestions[link_index]))
				eventData.cid = getCourseId()
				sendEvent('clickedSuggestion', eventData)
			})
		});
	}
}

function clearSuggestions() {
	$("#rec_link_list").empty()
}

function removeSearchResultsHeader() {
	$("#search-results-header").empty()
}

function insertSearchResultsHeader() {
	if ($("#search-results-header")[0].innerHTML === "") {
		$("#search-results-header").append(searchResultsHeaderHtml)
	} 
	
}

function sendEvent(eventType, eventData) {
	browser.runtime.sendMessage({
		type: 'event', 
		eventType: eventType, 
		eventData: eventData
	})
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
	var body = ""
	if (!($('#rich_old_new_post_ifr')[0] === undefined)) {
		var body_iframe = $('#rich_old_new_post_ifr')[0].contentWindow;
		body = body_iframe.document.getElementsByTagName('p')[0].innerText;
	}
	else {
		body = $("#rich_old_new_post").val()
	}

	var tag_texts = getTags();
	var word_list = [];

	var summary = $('#post_summary').val();

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
		clearTimeout(timeout)
		timeout = setTimeout(callback, delay)
	}
}
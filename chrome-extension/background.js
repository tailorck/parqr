chrome.extension.onMessage.addListener(function(request, sender, sendResponse) {
	console.log(request)
	/*
	setTimeout(function() {
		sendResponse({
			"0.17566": {
				"pid": 24,
				"subject": "run script.py"
			},
			"0.17831": {
				"pid": 40,
				"subject": "Tweepy methods"
			},
			"0.18689": {
				"pid": 319,
				"subject": "loading data into HDFS"
			},
			"0.21342": {
				"pid": 47,
				"subject": "Installing Tweepy"
			},
			"0.22952": {
				"pid": 111,
				"subject": "HW1 Q1"
			}
		});
	}, 5000);
	*/
	var url = "http://localhost:8000/api/similar_posts";
	var requestJson = {};
	requestJson['query'] = request['words'];
	requestJson['cid'] = request['cid'];
	requestJson['N'] = 5;

	var http = new XMLHttpRequest();
	http.open("POST", url, true);
	http.setRequestHeader("Content-type", "application/json");

	http.onreadystatechange = function() {
		if(http.readyState == 4) {
			if(http.status == 500) {
				console.log(http.response);	
			} else {
				console.log(http.response);
				sendResponse(http.response);
			}
		}
	}

	console.log(requestJson)
	http.send(JSON.stringify(requestJson))

	console.log('Retrieving posts from API');
	return true;
});




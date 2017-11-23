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
	var host = "http://ec2-54-227-24-100.compute-1.amazonaws.com/"
    request["type"] = "query";

    if (request["type"] == "query"){
        get_similar_posts(host, request, sender, sendResponse)
    }else if(request["type"] == "click"){
        get_click_rate(host, request, sender, sendResponse)
    }

	return true;
});


function get_similar_posts(host, request, sender, sendResponse) {

    var endpoint = host + "api/similar_posts";
	var requestJson = {};
	requestJson['query'] = request['words'];
	requestJson['cid'] = request['cid'];
	requestJson['N'] = 5;

	requestJson = add_cookie(requestJson);

	var http = new XMLHttpRequest();
	http.open("POST", endpoint, true);
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

    requestJson['time'] = new Date().valueOf();
	console.log(requestJson)
	http.send(JSON.stringify(requestJson))

	console.log('Retrieving posts from API');
}


function add_cookie(requestJson) {

    chrome.cookies.get({
	    url: 'http://piazza.com',
	    name: 'uid'
	},
    function (cookie) {
        if (cookie) {
            console.log('Retrieving Cookie Value!');
            console.log(cookie.value);
            requestJson['uid'] = cookie.value
        }
        else {
            console.log('Setting new Cookie Value!');
            chrome.cookies.set({
                "name": "uid",
                "url": "http://piazza.com",
                "value": gen_hash(),
            }, function (cookie) {
                console.log(JSON.stringify(cookie));
                requestJson['uid'] = cookie.value
            });
        }
    });

    return requestJson;
}

function gen_hash() {
    var rand = Math.random();
    while(rand == 0) {
        rand = Math.random();
    }

    var time_ms = new Date().valueOf();
    var prod = rand * time_ms;
    prod = prod.toString().replace('.','');
    return prod;
}

function get_click_rate(host, request, sender, sendResponse) {

    var endpoint = host + "api/click";
	var requestJson = {};
	requestJson['time'] = new Date().valueOf();
	requestJson['pid'] = request['pid'];
	requestJson['uid'] = request['uid'];
	requestJson['cid'] = request['cid'];

	var http = new XMLHttpRequest();
	http.open("POST", endpoint, true);
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



}
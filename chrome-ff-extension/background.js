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

browser.runtime.onMessage.addListener(function(request, sender, sendResponse) {
    var host = "http://ec2-54-198-200-115.compute-1.amazonaws.com/"

    if (request["type"] == "query"){
        get_similar_posts(host, request, sender, sendResponse)
    } else if(request["type"] == "click"){
        get_click_rate(host, request, sender, sendResponse)
    } else if (request["type"] == "event") {
        post_event(host, request['eventType'], request['eventData'])
    }
    return true;
});

function post_event(host, eventName, eventData) {
    var endpoint = host + "api/event"
    var requestJson = {
        type: "event",
        eventName: eventName,
        eventData: eventData,
        time: new Date().valueOf()
    }

    getCookie(function(cookie_val) {
        requestJson['uid'] = cookie_val
        var req = new XMLHttpRequest();
        req.open("POST", endpoint, true)
        req.send(JSON.stringify(requestJson))
        console.log(JSON.stringify(requestJson))
    })
}

function get_similar_posts(host, request, sender, sendResponse) {
    var endpoint = host + "api/similar_posts";
    var requestJson = {
        query: request['words'],
        cid: request['cid'],
        N: 5,
        time: new Date().valueOf()
    };

    getCookie(function(cookie_val) {
        requestJson['uid'] = cookie_val
        var req = new XMLHttpRequest();
        req.open("POST", endpoint, true)
        req.setRequestHeader("Content-type", "application/json");

        req.onreadystatechange = function() {
            if(req.readyState === XMLHttpRequest.DONE && req.status === 200) {
                sendResponse(JSON.parse(req.responseText))
            }
        }

        req.send(JSON.stringify(requestJson))
    })
}

function getCookie(callback) {

    chrome.cookies.get({
        url: 'http://piazza.com',
        name: 'uid'
    },
    function (cookie) {
        if (cookie) {
            callback(cookie.value)
        }
        else {
            chrome.cookies.set({
                "name": "uid",
                "url": "http://piazza.com",
                "value": gen_hash(),
            }, function (cookie) {
                callback(cookie.value)
            });
        }
    });
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

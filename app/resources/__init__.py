course = {
    "type": "object",
    "properties": {
        "course_id": { "type": "string" }
    },
    "required": ["course_id"]
}

event = {
    "type": "object",
    "properties": {
        "course_id": { "type": "string" }
    },
    "required": ["course_id"]
}

feedback_schema = {
    "type": "object",
    "properties": {
        "course_id" : { "type": "string" },
        "user_id" : { "type": "string" },
        "query_recommendation_id" : {"type": "string"},
        "feedback_pid": { "type": "number" },
        "user_rating": { "type": "number" }
    },
    "required": ["course_id", "user_id", "query_recommendation_id", "feedback_pid", "user_rating"]
}

query = {
    "type": "object",
    "properties": {
        "query": { "type": "string" },
        "course_id": { "type": "string" }
    },
    "required": ["query", "course_id"]
}

train_model = {
    "type": "object",
    "properties": {
        "course_id": { "type": "string" }
    },
    "required": ["course_id"]
}

user = {
    "type": "object",
    "properties": {
        "username": { "type": "string" },
        "password": { "type": "string" }
    },
    "required": ["username", "password"]
}

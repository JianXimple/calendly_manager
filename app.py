
import json
import requests
from openai import OpenAI
from tenacity import retry, wait_random_exponential, stop_after_attempt
import streamlit as st
import os
CALENDLY_API_KEY = os.getenv("CALENDLY_API_KEY")
GPT_MODEL = "gpt-3.5-turbo-0613"
client = OpenAI()

@retry(wait=wait_random_exponential(multiplier=1, max=40), stop=stop_after_attempt(3))
def chat_completion_request(messages, tools=None, tool_choice=None, model=GPT_MODEL):
    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools,
            tool_choice=tool_choice,
        )
        return response
    except Exception as e:
        print("Unable to generate ChatCompletion response")
        print(f"Exception: {e}")
        return e

tools = [
    {
        "type": "function",
        "function": {
            "name": "list_events",
            "description": "List scheduled events",
        }
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_event",
            "description": "Cancel a scheduled event",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_input": {
                        "type": "string",
                        "description": "cancel one event that matches user input description",
                    }
                },
                "required": ["user_input"]
            },
        }
    }
]


def list_events():
    
    url = "https://api.calendly.com/scheduled_events"
    querystring = {"user":"https://api.calendly.com/users/3e1d3371-b97f-44d3-80c5-d1997dcc9c0e"}
    headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {CALENDLY_API_KEY}",
    }
    response = requests.request("GET", url, headers=headers,params=querystring)
    response_data = json.loads(response.text)

# Extracting event UUIDs
    event_uuids = [event['uri'].split('/')[-1] for event in response_data['collection']]
    # print(event_uuids)
    return response_data['collection']
def cancel_event_by_id(uuid):
    # uuid="29f80d48-3859-4d12-b095-599c805e3490"
    url = f"https://api.calendly.com/scheduled_events/{uuid}/cancellation"
    payload = {"reason": "test"}
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {CALENDLY_API_KEY}"
    }

    response = requests.request("POST", url, json=payload, headers=headers)
    
def is_matching_event(user_input, event_details):
    messages = [
        {"role": "system", "content": "User wants to match an event based on time."},
        {"role": "user", "content": user_input},
        {"role": "assistant", "content": f"Event details: {event_details}"},
        {"role": "user", "content": "Is this the event that matches my requirement? Yes or no?"}
    ]
    response = chat_completion_request(messages)
    if response.choices:
        return "yes" in response.choices[0].message.content.lower()
    return False

def find_event_uuid(user_input):
    events = list_events()
    for event in events:
        event_details = json.dumps(event)
        if is_matching_event(user_input, event_details):
            return event['uri'].split('/')[-1]
    return None
def cancel_event(user_input):
    uuid=find_event_uuid(user_input)
    if uuid:
        cancel_event_by_id(uuid)
        print("canceled: ",uuid)
        return True
    else:
        print('fail to cancel')
        return False


st.title("Event Management Chatbot")

user_input = st.text_input("Enter your message:")

if st.button("Send"):
    messages = [
        {"role": "system", "content": "Don't make assumptions about what values to plug into functions. Ask for clarification if a user request is ambiguous."},
        {"role": "user", "content": user_input}
    ]
    chat_response = chat_completion_request(messages, tools=tools)
    assistant_message = chat_response.choices[0].message
    st.write(assistant_message.content)

    
    for tool_call in assistant_message.tool_calls:
        function_name = tool_call.function.name
        arguments = tool_call.function.arguments

        if function_name == "list_events":
            result = list_events()
            st.write(result)
        elif function_name == "cancel_event":
            arguments=json.loads(arguments)
            user_input = arguments.get("user_input")
            result = cancel_event(user_input)
            st.write("Event cancelled" if result else "Failed to cancel event")


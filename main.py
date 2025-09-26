import os 
from google import genai
from dotenv import load_dotenv
from rich.panel import Panel
from rich.console import Console
import json
import streamlit as st


st.title("My Agent")

console = Console()

load_dotenv()

model = "gemini-1.5-flash"

system_prompt = """
You are a Question/Answer agent.

Create and manage structured task lists for tracking progress through workflows.
##IMPORTANT 
ALWAYS USE TO-DO LIST.EVEN FOR SIMPLE TASK. BEFORE WRITING CHECK TO-DO LIST.
## Structure                                                                                                   
│  - Maintain one list containing multiple todo objects (content, status)
│  - Use clear, actionable content descriptions                                                                   
│  - Status must be: pending, in_progress, or completed   

## Best Practices                                                                                              
│  - Only one in_progress task at a time                                                                          
│  - Mark completed immediately when task is fully done                                                           
│  - Always send the full updated list when making changes                                                        
│  - Prune irrelevant items to keep list focused 

## Progress Updates                                                                                            
│  - Call write_todo again to change task status or edit content                                                   
│  - Reflect real-time progress; don't batch completions                                                          
│  - If blocked, keep in_progress and add new task describing blocker                                             

Respond with EXACTLY ONE of these formats:
1. FUNCTION_CALL: python_function_name|input
2. FINAL_ANSWER: Answer for the question

where python_function_name is one of the following:
1. read_todo() It gives back the list of to-do and their status.
2. write_todo(to_do) It takes list of dict with content and status and gives back updated 
2. get_weather(string) It takes a word as input and returns weather in a particular location.                                                  │

DO NOT include multiple responses. Give ONE response at a time.
"""

max_iteration = 10

to_do_list = []

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "ai",
            "content": "Hello !! How can I help You Today!!"
        }
    ]

def read_todo():
    global to_do_list
    return f"Here is the {to_do_list}"

def write_todo(to_do):
    global to_do_list
    to_do_list = json.loads(to_do)
    return f"Updated {to_do_list} successfully"

def gemini_llm():
    api_key = os.getenv("GOOGLE_API_KEY", "UNKNOWN")
    client = genai.Client(api_key=api_key)
    return client

def get_weather(location: str) -> str:
    
    return f"Its sunny in {location}"

def function_caller(func_name, params):
    """Simple function caller that maps function names to actual functions"""
    function_map = {
        "get_weather" : get_weather,
        "write_todo" : write_todo,
        "read_todo" : read_todo
    }
    
    if func_name in function_map:
        return function_map[func_name](params)
    else:
        return f"Function {func_name} not found"


def invoke(current_query, container):
    global max_iteration, model, system_prompt, to_do_list
    iteration = 0
    iteration_response = []
    client = gemini_llm()
    thoughts_placeholder = container.container()
    todo_placeholder = thoughts_placeholder.empty()

    console.print(Panel(system_prompt, title="⚙️ System", border_style="white"))
    
    console.print(Panel(current_query, title="🧑 Human", border_style="purple"))

    with thoughts_placeholder.expander("Peak into Inside", expanded=True) as tb:
       
        while iteration < max_iteration:
            console.print(Panel(f"\n--- Iteration {iteration + 1} ---", title="📜 LOGS", border_style="white"))
            if iteration_response:
                current_query = current_query + "\n\n" + " ".join(iteration_response)
                current_query = current_query + "  What should I do next?"

            # Get model's response
            prompt = f"{system_prompt}\n\nQuery: {current_query}"
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            
            response_text = response.text.strip()
            console.print(Panel(response_text, title="🤖 Assistant", border_style="light_sea_green"))
            if response_text.startswith("FUNCTION_CALL:"):
                status_placeholder = st.empty()
                response_text = response.text.strip()
                _, function_info = response_text.split(":", 1)
                func_name, params = [x.strip() for x in function_info.split("|", 1)]
                if "todo" not in func_name:
                    with status_placeholder.status("Using Tool....", expanded=True) as sp: 
                        st.write(func_name)
                        st.code(params)
                        iteration_result = function_caller(func_name, params)
                        st.write("tool output: ")
                        st.code(iteration_result)
                        sp.update(label="Completed Calling Tool!", expanded=False)
                elif "write_todo" in func_name:
                    with todo_placeholder.status("TO-DO", expanded=True) as tp:
                        iteration_result = function_caller(func_name, params)
                        for task in to_do_list:
                            if task["status"] == "pending":
                                st.markdown(f"- [ ] {task['content']}")
                            elif task["status"] == "in_progress":
                                st.markdown(f"🔄 **{task['content']}**")
                            elif task["status"] == "completed":
                                st.markdown(f"- [x] ~~{task['content']}~~")

            # Check if it's the final answer
            elif response_text.startswith("FINAL_ANSWER:"):
                console.print(Panel("==== Agent Execution Complete ===", title= "🕵🏻 AGENT", border_style="green"))
                _,result = response_text.strip().split(":", 1)
                return result
            iteration_response.append(f"In the {iteration + 1} iteration you called {func_name} with {params} parameters, and the function returned {iteration_result}.")

            iteration += 1
    return "Max limit reached"

for msg in st.session_state.messages:

    if msg["role"] == "user":
        st.chat_message("user").write(msg["content"])
    elif msg["role"] == "ai":
        st.chat_message("assistant").write(msg["content"])

if prompt := st.chat_input():
    st.session_state.messages.append({
        "role": "user", 
        "content": prompt
    })
    st.chat_message("user").write(prompt)

    with st.chat_message("assistant"):
        
        response = invoke(
            prompt, st.container()
        )
        st.write(response.strip())
        st.session_state.messages.append({
            "role": "ai",
            "content": response 
        })
import streamlit as st
import json
import os
from google import genai
from tavily import TavilyClient
from time import sleep

import config as cfg

from rich.console import Console
from rich.panel import Panel
console = Console()

class ResearchAgent():

    def __init__(self, model, system_prompt):

        self.model = model

        self.system_prompt = system_prompt

        self.max_iteration = 10

        tavily_api_key = os.getenv("TAVILY_API_KEY", "UNKNOWN")

        self.client = TavilyClient(api_key=tavily_api_key)


    def tavily_search(self, query):

        results = self.client.search(
            query=query
        )

        return json.dumps(results)
    

    def gemini_llm(self, *args):
        api_key = os.getenv("GOOGLE_API_KEY", "UNKNOWN")
        client = genai.Client(api_key=api_key)
        return client
    
    def list_files_name(self, *args):

        return f"Available files in memory is {list(st.session_state.files.keys())}"
    
    def write_file(self, content):
        file = json.loads(content)
        st.session_state.files.update({
            file["file_name"]: file["content"]
        })

        full_path = os.path.join(cfg.RESEARCH_CONTENT_PATH, file["file_name"])
        with open(full_path, 'w') as f:
            f.write(file["content"])

    def think_tool(self, reflection: str):

        return f"Reflection recorded: {reflection}"

    def function_caller(self, func_name, params):
        """Simple function caller that maps function names to actual functions"""
        function_map = {
            "tavily_search" : self.tavily_search,
            "list_files_name" : self.list_files_name,
            "write_file": self.write_file,
            "think_tool": self.think_tool
        }
    
        if func_name in function_map:
            return function_map[func_name](params)
        else:
            return f"Function {func_name} not found"


    def invoke(self, current_query):
        iteration = 0
        iteration_response = []
        client = self.gemini_llm()
        thoughts_placeholder = st.container()

        console.print(Panel(cfg.RESEARCH_AGENT, title="⚙️ System", border_style="white"))
        
        console.print(Panel(current_query, title="🧑 Human", border_style="purple"))

        with thoughts_placeholder.expander("Research Agent..", expanded=True) as tb:
        
            while iteration < self.max_iteration:
                console.print(Panel(f"\n--- Research Iteration {iteration + 1} ---", title="📜 LOGS", border_style="white"))
                iteration_result = ""
                if iteration_response:
                    current_query = current_query + "\n\n" + " ".join(iteration_response)
                    current_query = current_query + "  What should I do next?"

                # Get model's response
                prompt = f"{self.system_prompt}\n\nQuery: {current_query}"
                response = client.models.generate_content(
                    model=self.model,
                    contents=prompt
                )
                
                response_text = response.text.strip()
                console.print(Panel(response_text, title="🤖 Assistant", border_style="light_sea_green"))
                if response_text.startswith("FUNCTION_CALL:"):
                    status_placeholder = st.empty()
                    response_text = response.text.strip()
                    _, function_info = response_text.split(":", 1)
                    func_name, params = [x.strip() for x in function_info.split("|", 1)]
                    with status_placeholder.status("Using Tool....", expanded=True) as sp: 
                        st.write(func_name)
                        st.code(params)
                        iteration_result = self.function_caller(func_name, params)
                        st.write("tool output: ")
                        st.code(iteration_result)
                        sp.update(label="Completed Calling Tool!", expanded=False)

                # Check if it's the final answer
                elif response_text.startswith("FINAL_ANSWER:"):
                    console.print(Panel("==== Agent Execution Complete ===", title= "🕵🏻 AGENT", border_style="green"))
                    _,result = response_text.strip().split(":", 1)
                    return result
                iteration_response.append(f"In the {iteration + 1} iteration you called {func_name} with {params} parameters, and the function returned {iteration_result}.")
                iteration += 1
                sleep(1)

        return "Max limit reached"
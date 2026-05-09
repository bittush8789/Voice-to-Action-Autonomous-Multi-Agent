import json
import logging
from typing import TypedDict, List, Dict, Any
from langgraph.graph import StateGraph, START, END

# Import Services & Tools
from backend.services.groq_service import groq_service
from backend.services.db_service import save_workflow_run
from backend.memory.chroma_service import memory_service
from backend.langchain.prompts.agent_prompts import (
    INTENT_AGENT_SYSTEM_PROMPT,
    PLANNING_AGENT_SYSTEM_PROMPT,
    SUMMARY_AGENT_SYSTEM_PROMPT
)

# Import Tool executors
from backend.tools.email_tool import send_email
from backend.tools.slack_tool import send_slack_notification
from backend.tools.jira_tool import create_jira_ticket
from backend.tools.github_tool import create_github_issue
from backend.tools.calendar_tool import schedule_meeting
from backend.tools.report_tool import generate_report
from backend.tools.search_tool import perform_search

logger = logging.getLogger(__name__)

# 1. Define State
class AgentState(TypedDict):
    audio_path: str
    text_input: str  # Direct text input fallback
    transcript: str
    intent: str
    parameters: Dict[str, Any]
    plan: List[str]
    memory_context: List[Dict[str, Any]]
    tool_output: Dict[str, Any]
    summary: str
    logs: List[str]

# 2. Define Node Functions
def voice_agent_node(state: AgentState) -> Dict[str, Any]:
    logs = state.get("logs", []).copy()
    logs.append("[Voice Agent] Active: Processing input audio.")
    
    transcript = ""
    if state.get("audio_path"):
        try:
            transcript = groq_service.transcribe_audio(state["audio_path"])
            logs.append(f"[Voice Agent] Successfully transcribed audio using Whisper: '{transcript}'")
        except Exception as e:
            logs.append(f"[Voice Agent] Failed transcription ({e}).")
            transcript = state.get("text_input", "")
    else:
        transcript = state.get("text_input", "")
        logs.append(f"[Voice Agent] No audio file provided. Proceeding with text input: '{transcript}'")
        
    return {"transcript": transcript, "logs": logs}

def intent_agent_node(state: AgentState) -> Dict[str, Any]:
    logs = state.get("logs", []).copy()
    logs.append("[Intent Agent] Active: Parsing user intent.")
    
    transcript = state.get("transcript", "")
    intent = "unspecified"
    parameters = {}
    
    try:
        response_str = groq_service.chat_completion(
            system_prompt=INTENT_AGENT_SYSTEM_PROMPT,
            user_prompt=f"User command: '{transcript}'",
            response_format="json"
        )
        data = json.loads(response_str)
        intent = data.get("intent", "unspecified")
        parameters = data.get("parameters", {})
        logs.append(f"[Intent Agent] Parsed Intent: '{intent}' with parameters: {json.dumps(parameters)}")
    except Exception as e:
        logs.append(f"[Intent Agent] Error parsing intent ({e}). Attempting simulation parsing.")
        # Sim fallback
        if "email" in transcript.lower():
            intent, parameters = "send_email", {"recipient": "devops@company.com", "subject": "Alert", "message": "System check success"}
        else:
            intent, parameters = "general_question", {"question": transcript}
            
    return {"intent": intent, "parameters": parameters, "logs": logs}

def planning_agent_node(state: AgentState) -> Dict[str, Any]:
    logs = state.get("logs", []).copy()
    logs.append("[Planning Agent] Active: Formulating step-by-step execution plan.")
    
    intent = state.get("intent", "")
    parameters = state.get("parameters", {})
    plan = []
    
    try:
        response_str = groq_service.chat_completion(
            system_prompt=PLANNING_AGENT_SYSTEM_PROMPT,
            user_prompt=f"Intent: {intent}\nParameters: {json.dumps(parameters)}",
            response_format="json"
        )
        plan = json.loads(response_str)
        logs.append(f"[Planning Agent] Formulated plan: {json.dumps(plan)}")
    except Exception as e:
        logs.append(f"[Planning Agent] Error generating plan ({e}). Using default templates.")
        plan = [f"Initialize {intent} operation", f"Execute action with params {json.dumps(parameters)}"]
        
    return {"plan": plan, "logs": logs}

def memory_agent_node(state: AgentState) -> Dict[str, Any]:
    logs = state.get("logs", []).copy()
    logs.append("[Memory Agent] Active: Querying ChromaDB Vector database for workflow context.")
    
    transcript = state.get("transcript", "")
    memories = []
    
    try:
        memories = memory_service.search_memory(transcript, limit=2)
        if memories:
            logs.append(f"[Memory Agent] Found {len(memories)} matching historical memories/workflows in ChromaDB.")
            # If the user requested "same as yesterday", we can reuse the historical parameters if desired
            if "same" in transcript.lower() or "yesterday" in transcript.lower() or "previous" in transcript.lower():
                logs.append("[Memory Agent] Memory Context matches reuse trigger! Recovering historical parameters.")
                best_match = memories[0]
                state["parameters"] = best_match["parameters"]
                logs.append(f"[Memory Agent] Replaced parameters with historical memory: {json.dumps(best_match['parameters'])}")
        else:
            logs.append("[Memory Agent] No closely matching historical workflows found.")
    except Exception as e:
        logs.append(f"[Memory Agent] Error performing Chroma search ({e}).")
        
    return {"memory_context": memories, "parameters": state["parameters"], "logs": logs}

def tool_agent_node(state: AgentState) -> Dict[str, Any]:
    logs = state.get("logs", []).copy()
    logs.append("[Tool Agent] Active: Performing dynamic tool selection and execution.")
    
    intent = state.get("intent", "")
    parameters = state.get("parameters", {})
    tool_output = {"status": "skipped", "log": "No tool matched the parsed intent."}
    
    try:
        if intent == "send_email":
            tool_output = send_email(
                recipient=parameters.get("recipient", "team@company.com"),
                subject=parameters.get("subject", "Automated Update"),
                message=parameters.get("message", "No content provided.")
            )
        elif intent == "notify_slack":
            tool_output = send_slack_notification(
                channel=parameters.get("channel", "#general"),
                message=parameters.get("message", "Ping!")
            )
        elif intent == "create_jira_ticket":
            tool_output = create_jira_ticket(
                project_key=parameters.get("project_key", "PROJ"),
                summary=parameters.get("summary", "New Ticket"),
                description=parameters.get("description", ""),
                issue_type=parameters.get("issue_type", "Task"),
                priority=parameters.get("priority", "Medium")
            )
        elif intent == "create_github_issue":
            tool_output = create_github_issue(
                repo=parameters.get("repo", "workspace/repo"),
                title=parameters.get("title", "Issue"),
                body=parameters.get("body", "")
            )
        elif intent == "schedule_meeting":
            tool_output = schedule_meeting(
                title=parameters.get("title", "Meeting"),
                date=parameters.get("date", "2026-05-10"),
                time_str=parameters.get("time_str", "10:00 AM"),
                attendees=parameters.get("attendees", []),
                duration_minutes=int(parameters.get("duration_minutes", 30))
            )
        elif intent == "generate_report":
            tool_output = generate_report(
                topic=parameters.get("topic", "System Summary"),
                content_source=parameters.get("content_source", "Database logs"),
                format_type=parameters.get("format_type", "Markdown")
            )
        elif intent == "perform_search":
            tool_output = perform_search(
                query=parameters.get("query", "")
            )
        elif intent == "general_question":
            question = parameters.get("question", "")
            system_prompt = (
                "You are a highly advanced, ultra-intelligent, and extremely helpful AI assistant. "
                "Provide a beautifully formatted, comprehensive, and clear answer to the user's question, "
                "using markdown, lists, or headers where appropriate."
            )
            ans = groq_service.chat_completion(
                system_prompt=system_prompt,
                user_prompt=question,
                response_format="text"
            )
            tool_output = {
                "status": "success",
                "tool": "General QA Tool",
                "log": ans
            }
            
        logs.append(f"[Tool Agent] Tool response: {tool_output.get('log', 'Success')}")
    except Exception as e:
        error_msg = f"Failed executing tool for intent '{intent}' due to: {e}"
        logs.append(f"[Tool Agent] {error_msg}")
        tool_output = {"status": "error", "log": error_msg}
        
    return {"tool_output": tool_output, "logs": logs}

def summary_agent_node(state: AgentState) -> Dict[str, Any]:
    logs = state.get("logs", []).copy()
    logs.append("[Summary Agent] Active: Compiling final summary report and updating memory stores.")
    
    transcript = state.get("transcript", "")
    intent = state.get("intent", "")
    parameters = state.get("parameters", {})
    plan = state.get("plan", [])
    tool_output = state.get("tool_output", {})
    
    summary = ""
    try:
        if intent == "general_question":
            summary = tool_output.get("log", "")
            logs.append("[Summary Agent] Directly using compiled QA response as summary.")
        else:
            user_prompt = f"""
            User command: '{transcript}'
            Parsed Intent: '{intent}'
            Parameters: {json.dumps(parameters)}
            Plan: {json.dumps(plan)}
            Tool Output: {json.dumps(tool_output)}
            """
            summary = groq_service.chat_completion(
                system_prompt=SUMMARY_AGENT_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                response_format="text"
            )
            logs.append("[Summary Agent] Compiled premium summary successfully.")
    except Exception as e:
        logs.append(f"[Summary Agent] Error compiling summary ({e}). Falling back to simple summary.")
        summary = f"Operation '{intent}' completed successfully. Details: {tool_output.get('log', 'N/A')}"
        
    # Persist the successful execution to SQLite History and ChromaDB Semantic memory
    try:
        run_id = save_workflow_run(
            transcript=transcript,
            intent=intent,
            parameters=parameters,
            plan=plan,
            tool_executed=tool_output.get("tool", "Unspecified Tool"),
            tool_output=tool_output,
            summary=summary,
            status="Success" if tool_output.get("status") == "success" else "Failed"
        )
        logs.append(f"[Summary Agent] Workflow run saved in SQLite DB (ID: {run_id}).")
        
        # Store in ChromaDB Memory
        memory_service.store_memory(
            user_command=transcript,
            summary=summary,
            workflow_plan=plan,
            tool=tool_output.get("tool", "Unspecified Tool"),
            parameters=parameters
        )
        logs.append("[Summary Agent] Command and execution outcome indexed in ChromaDB.")
    except Exception as e:
        logs.append(f"[Summary Agent] Database persistence error ({e}).")
        
    return {"summary": summary, "logs": logs}

# 3. Assemble LangGraph StateGraph
workflow = StateGraph(AgentState)

# Add Nodes
workflow.add_node("voice_agent", voice_agent_node)
workflow.add_node("intent_agent", intent_agent_node)
workflow.add_node("planning_agent", planning_agent_node)
workflow.add_node("memory_agent", memory_agent_node)
workflow.add_node("tool_agent", tool_agent_node)
workflow.add_node("summary_agent", summary_agent_node)

# Add Edges (START -> Voice -> Intent -> Planning -> Memory -> Tool -> Summary -> END)
workflow.add_edge(START, "voice_agent")
workflow.add_edge("voice_agent", "intent_agent")
workflow.add_edge("intent_agent", "planning_agent")
workflow.add_edge("planning_agent", "memory_agent")
workflow.add_edge("memory_agent", "tool_agent")
workflow.add_edge("tool_agent", "summary_agent")
workflow.add_edge("summary_agent", END)

# Compile workflow
app_workflow = workflow.compile()

# talent_scout_chatbot.py
import streamlit as st
import openai
import re
import ast
from typing import List, Dict

# Initialize session state
def initialize_session_state():
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    if "collected_data" not in st.session_state:
        st.session_state.collected_data = {
            "full_name": None,
            "email": None,
            "phone": None,
            "years_of_experience": None,
            "desired_position": None,
            "current_location": None,
            "tech_stack": None
        }
    
    if "conversation_state" not in st.session_state:
        st.session_state.conversation_state = "greeting"
    
    if "technical_questions" not in st.session_state:
        st.session_state.technical_questions = []
    
    if "current_question_index" not in st.session_state:
        st.session_state.current_question_index = -1

# Configure OpenAI API
def configure_openai(api_key: str):
    openai.api_key = api_key

# System prompts for different states
def get_system_prompt(state: str) -> str:
    prompts = {
        "greeting": (
            "You are an AI Hiring Assistant for TalentScout, a recruitment agency specializing in technology placements. "
            "Greet the candidate warmly and briefly explain that you'll help with the initial screening process. "
            "Ask if they're ready to begin. Keep your response under 2 sentences."
        ),
        "collect_info": (
            "You are collecting candidate information for TalentScout. "
            "Ask for the following details one at a time in this order: "
            "1. Full Name, 2. Email Address, 3. Phone Number, "
            "4. Years of Experience, 5. Desired Position(s), "
            "6. Current Location, 7. Tech Stack (programming languages, frameworks, databases, tools). "
            "Be friendly and conversational. After each response, confirm the information "
            "and move to the next item. Format: 'Great! Next, I need your [next item]'."
        ),
        "generate_questions": (
            "Based on the candidate's tech stack, generate 3-5 technical questions. "
            "Focus on core concepts and practical applications. "
            "Format questions as a Python list: ['Question 1', 'Question 2']"
        ),
        "technical_screening": (
            "You are conducting a technical screening. Ask one technical question at a time. "
            "After the candidate answers, simply move to the next question. "
            "Do not evaluate answers or provide feedback."
        ),
        "end_conversation": (
            "Thank the candidate for their time and inform them that: "
            "1. Their information has been recorded, "
            "2. The recruitment team will review their application, "
            "3. They'll be contacted within 3 business days. "
            "Wish them a great day and end the conversation."
        )
    }
    return prompts.get(state, "Please continue the conversation.")

# Get LLM response
def get_llm_response(messages: List[Dict], model="gpt-3.5-turbo") -> str:
    try:
        response = openai.ChatCompletion.create(
            model=model,
            messages=messages,
            temperature=0.7,
            max_tokens=150
        )
        return response.choices[0].message['content'].strip()
    except Exception as e:
        st.error(f"Error connecting to OpenAI: {str(e)}")
        return "I'm having trouble processing your request. Please try again later."

# Validate and format collected data
def validate_data(field: str, value: str) -> bool:
    validators = {
        "email": lambda v: re.match(r"[^@]+@[^@]+\.[^@]+", v),
        "phone": lambda v: re.match(r"^\+?[0-9\s\-\(\)]{7,}$", v),
        "years_of_experience": lambda v: v.isdigit() and 0 <= int(v) <= 50,
        "tech_stack": lambda v: len(v.split(',')) >= 1
    }
    
    if field in validators:
        return validators[field](value)
    return bool(value.strip())

# Generate technical questions
def generate_technical_questions(tech_stack: str) -> List[str]:
    prompt = [
        {"role": "system", "content": get_system_prompt("generate_questions")},
        {"role": "user", "content": f"Tech Stack: {tech_stack}"}
    ]
    
    response = get_llm_response(prompt)
    
    try:
        # Attempt to parse as Python list
        questions = ast.literal_eval(response)
        if isinstance(questions, list) and all(isinstance(q, str) for q in questions):
            return questions
    except:
        pass
    
    # Fallback if parsing fails
    return [
        f"Can you explain your experience with {tech_stack}?",
        f"What's the most challenging project you've completed using {tech_stack}?",
        f"How would you approach debugging a complex issue in {tech_stack.split(',')[0]}?"
    ]

# Handle conversation flow
def handle_conversation(user_input: str):
    # Check for exit keywords
    if any(word in user_input.lower() for word in ["exit", "quit", "end", "stop", "goodbye"]):
        st.session_state.conversation_state = "end_conversation"
    
    # Handle current state
    if st.session_state.conversation_state == "greeting":
        messages = [
            {"role": "system", "content": get_system_prompt("greeting")},
            {"role": "user", "content": user_input} if user_input else None
        ]
        messages = [m for m in messages if m is not None]
        
        response = get_llm_response(messages)
        st.session_state.messages.append({"role": "assistant", "content": response})
        st.session_state.conversation_state = "collect_info"
    
    elif st.session_state.conversation_state == "collect_info":
        # Identify next field to collect
        next_field = next(
            (field for field, value in st.session_state.collected_data.items() if value is None),
            None
        )
        
        if next_field:
            # Validate input if provided
            if user_input:
                if validate_data(next_field, user_input):
                    st.session_state.collected_data[next_field] = user_input
                    confirmation = f"Got it! {user_input} is recorded."
                    st.session_state.messages.append({"role": "assistant", "content": confirmation})
                else:
                    error_msg = {
                        "email": "Please enter a valid email address (e.g., name@example.com).",
                        "phone": "Please enter a valid phone number.",
                        "years_of_experience": "Please enter a number between 0 and 50.",
                        "tech_stack": "Please list at least one technology."
                    }.get(next_field, "Please provide a valid input.")
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})
                    return
            
            # Ask for next field or move to tech questions
            next_field = next(
                (field for field, value in st.session_state.collected_data.items() if value is None),
                None
            )
            
            if next_field:
                field_prompt = {
                    "full_name": "May I have your full name?",
                    "email": "What's your email address?",
                    "phone": "Could you share your phone number?",
                    "years_of_experience": "How many years of professional experience do you have?",
                    "desired_position": "What position(s) are you interested in?",
                    "current_location": "Where are you currently located?",
                    "tech_stack": "Please list your technical skills (e.g., Python, React, SQL):"
                }
                st.session_state.messages.append({"role": "assistant", "content": field_prompt[next_field]})
            else:
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": "Thanks for providing your information! Now I'll ask some technical questions."
                })
                st.session_state.technical_questions = generate_technical_questions(
                    st.session_state.collected_data["tech_stack"]
                )
                st.session_state.conversation_state = "technical_screening"
                st.session_state.current_question_index = 0
    
    elif st.session_state.conversation_state == "technical_screening":
        if st.session_state.current_question_index < len(st.session_state.technical_questions):
            # Ask next question
            question = st.session_state.technical_questions[st.session_state.current_question_index]
            st.session_state.messages.append({"role": "assistant", "content": question})
            st.session_state.current_question_index += 1
            
            # Move to end if all questions asked
            if st.session_state.current_question_index >= len(st.session_state.technical_questions):
                st.session_state.conversation_state = "end_conversation"
    
    elif st.session_state.conversation_state == "end_conversation":
        messages = [
            {"role": "system", "content": get_system_prompt("end_conversation")},
            {"role": "user", "content": user_input} if user_input else None
        ]
        messages = [m for m in messages if m is not None]
        
        response = get_llm_response(messages)
        st.session_state.messages.append({"role": "assistant", "content": response})

# Main app function with chat input text fix
def main():
    st.set_page_config(
        page_title="TalentScout Hiring Assistant",
        page_icon="💼",
        layout="centered"
    )
    
    # Custom CSS for styling including chat input fix
    st.markdown("""
    <style>
        /* Fix for chat input text visibility */
        textarea[data-baseweb="input"] {
            min-height: 100px;
            font-size: 18px;
            padding: 12px;
        }
        
        .stChatMessage {
            padding: 12px; 
            border-radius: 12px; 
            margin: 8px 0;
        }
        
        .assistant-message {
            background-color: #f0f5ff;
        }
        
        .user-message {
            background-color: #f0fff4;
        }
        
        .stButton button {
            background-color: #4CAF50; 
            color: white;
        }
    </style>
    """, unsafe_allow_html=True)
    
    st.title("💼 TalentScout Hiring Assistant")
    st.caption("AI-powered initial screening for tech candidates")
    
    # API key input
    api_key = st.sidebar.text_input("Enter OpenAI API Key:", type="password")
    if not api_key:
        st.info("Please enter your OpenAI API key to continue")
        st.stop()
    configure_openai(api_key)
    
    # Initialize session state
    initialize_session_state()
    
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Handle initial greeting if no messages
    if not st.session_state.messages:
        handle_conversation("")
        st.stop()
    
    # User input
    if user_input := st.chat_input("Type your response here..."):
        st.session_state.messages.append({"role": "user", "content": user_input})
        handle_conversation(user_input)
        st.stop()
    
    # Display collected data
    if st.session_state.conversation_state != "greeting":
        with st.sidebar.expander("Collected Information"):
            for field, value in st.session_state.collected_data.items():
                if value:
                    st.write(f"**{field.replace('_', ' ').title()}:** {value}")

if __name__ == "__main__":
    main()

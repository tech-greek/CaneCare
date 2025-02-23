import streamlit as st
import requests
import pandas as pd


# Set up Streamlit app
st.set_page_config(page_title="UM Stress Detector", page_icon="🧠")
st.title("UM Stress Detector Chatbot 🤖💬")
st.write(
   "A chatbot that collects detailed information about your stress and provides a tailored, step-by-step plan with UM-specific resources.")


# API Endpoint
API_URL = "http://127.0.0.1:5000/chat"


# Create a persistent session to maintain cookies
if "requests_session" not in st.session_state:
   st.session_state.requests_session = requests.Session()
session_req = st.session_state.requests_session


# Initialize chat history
if "chat_history" not in st.session_state:
   st.session_state["chat_history"] = []


# Display welcome message on first load
if "welcome_shown" not in st.session_state:
   response = session_req.post(API_URL, json={})
   if response.status_code == 200:
       json_data = response.json()
       bot_response = json_data.get("message", json_data)
       st.session_state["chat_history"].append({"role": "bot", "text": bot_response})
       st.session_state["welcome_shown"] = True


# Create tabs for Chat and Dashboard
tab1, tab2 = st.tabs(["Chat", "Dashboard"])


##############################
# Chat Tab (Fix: Properly Display Messages & Input Box)
##############################
with tab1:
   # Render chat history first (messages appear above input field)
   for msg in st.session_state["chat_history"]:
       st.chat_message(msg["role"]).write(msg["text"])


   # Input box (ensuring it's BELOW the chat messages)
   user_input = st.chat_input("Type your response...")


   if user_input:
       # Append user message to chat history
       st.session_state["chat_history"].append({"role": "user", "text": user_input})


       with st.spinner("Thinking..."):
           # Send request to backend chatbot API
           response = session_req.post(API_URL, json={"message": user_input})


           if response.status_code == 200:
               json_data = response.json()


               # Extract bot response
               if "message" in json_data:
                   bot_response = json_data["message"]
               elif "detailed_plan" in json_data:
                   bot_response = (
                       f"Stress Area: {json_data.get('stress_area', 'Unknown')}\n\n"
                       f"{json_data.get('detailed_plan', 'No detailed plan provided.')}"
                   )
               else:
                   bot_response = str(json_data)


               # Append bot response to chat history
               st.session_state["chat_history"].append({"role": "bot", "text": bot_response})


               # Display bot response
               st.chat_message("bot").write(bot_response)
           else:
               st.error("Error: Unable to process your request. Try again.")


##############################
# Dashboard Tab (Fixed Layout)
##############################
with tab2:
   st.title("Dashboard")
   st.write("Manage your meetings and track your stress over time.")


   # --- Meeting Calendar ---
   st.subheader("Meeting Calendar")
   with st.form(key="schedule_form"):
       event_title = st.text_input("Event Title", "Meeting with UM Resource")
       event_date = st.date_input("Date")
       event_time = st.text_input("Time (e.g., 3:00 PM)")
       event_location = st.text_input("Location", "UM Campus")
       submitted = st.form_submit_button("Add to Schedule")


       if submitted:
           new_event = {
               "title": event_title,
               "date": event_date.strftime("%Y-%m-%d"),
               "time": event_time,
               "location": event_location
           }
           if "schedule" not in st.session_state:
               st.session_state["schedule"] = []
           st.session_state.schedule.append(new_event)
           st.success("Event added to your schedule!")


   if "schedule" in st.session_state and st.session_state.schedule:
       st.subheader("Your Scheduled Meetings")
       df_schedule = pd.DataFrame(st.session_state["schedule"])
       df_schedule["date"] = pd.to_datetime(df_schedule["date"])
       df_schedule = df_schedule.sort_values("date")


       for d, group in df_schedule.groupby(df_schedule["date"].dt.date):
           with st.expander(f"Meetings on {d}"):
               st.table(group[["title", "time", "location"]])


   # --- Stress Tracker ---
   st.subheader("Stress Tracker")
   if "stress_data" not in st.session_state:
       st.session_state.stress_data = []


   with st.form(key="stress_form"):
       stress_date = st.date_input("Select Date", key="stress_date")
       stress_rating = st.slider("How stressed are you today? (1 = least, 10 = most)", 1, 10, 5, key="stress_rating")
       stress_submitted = st.form_submit_button("Record Stress Level")


       if stress_submitted:
           st.session_state.stress_data.append({"date": stress_date, "rating": stress_rating})
           st.success("Stress level recorded!")


   if st.session_state.stress_data:
       stress_df = pd.DataFrame(st.session_state.stress_data)
       stress_df["date"] = pd.to_datetime(stress_df["date"])
       stress_df = stress_df.sort_values("date")
       st.line_chart(stress_df.set_index("date")["rating"])


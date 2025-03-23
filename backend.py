import os
import openai
from flask import Flask, request, jsonify, session
from flask_session import Session
from dotenv import load_dotenv


# Load environment variables (if needed)
load_dotenv()
openai_api_key = "" # enter key here 
openai.api_key = openai_api_key


# Flask App Setup
app = Flask(__name__)
app.secret_key = os.urandom(24)  # Required for session management
app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_PERMANENT"] = False
Session(app)


# Welcome message and initial domain selection question
WELCOME_MESSAGE = (
  "Hello! I'm your stress detection assistant. Let's chat about your current experiences and see how you're doing. 😊\n\n"
  "Type 'hello' to begin the process."
)


DOMAIN_SELECTION_QUESTION = (
  "Which area has been most challenging for you recently? Please choose one:\n"
  "[1] Academics\n"
  "[2] Mental Wellbeing\n"
  "[3] Physical Health\n"
  "[4] Social Life\n"
  "[5] Career Tension"
)


# Mapping of domain choices to their names
domain_map = {
  "1": "Academics",
  "2": "Mental Wellbeing",
  "3": "Physical Health",
  "4": "Social Life",
  "5": "Career Tension"
}


# Domain-specific questions – each domain has five in-depth questions
domain_specific_questions = {
  "1": [  # Academics
      "What course or subject is proving to be most challenging for you right now?",
      "Are you finding the course material difficult to understand, or is it more about the workload and deadlines?",
      "Do you have any upcoming deadlines, exams, or assignments that are causing extra pressure?",
      "Have you reached out for academic support such as tutoring, office hours, or study groups?",
      "What strategies have you tried so far to manage your academic challenges, and how effective have they been?"
  ],
  "2": [  # Mental Wellbeing
      "How have you been feeling emotionally over the past few weeks? (For example: anxious, sad, or overwhelmed)",
      "Do you experience frequent episodes of anxiety or depression? If so, how intense are these episodes?",
      "How has your sleep been? Do you find it hard to fall or stay asleep?",
      "Are there any personal or family issues that might be affecting your mental health?",
      "What coping mechanisms or self-care practices have you tried, and have they helped you manage your feelings?"
  ],
  "3": [  # Physical Health
      "How would you describe your overall physical health and energy levels?",
      "Do you experience any physical discomfort, pain, or fatigue that interferes with your daily activities?",
      "What does your typical sleep schedule look like? Do you get enough rest?",
      "How often do you engage in physical exercise or activities?",
      "What changes do you think might improve your physical well-being (e.g., nutrition, exercise, sleep habits)?"
  ],
  "4": [  # Social Life
      "How satisfied are you with your current social interactions and friendships?",
      "Do you feel that you have a supportive social network at UM?",
      "Have you experienced any conflicts or feelings of isolation in your social life recently?",
      "How do your social interactions affect your mood and stress levels?",
      "What would you like to change about your social interactions or support system?"
  ],
  "5": [  # Career Tension
      "What specific career or job-related concerns have been on your mind lately?",
      "Do you feel overwhelmed by the expectations or responsibilities of your current work or internship?",
      "How clear are you about your future career path, and do you feel prepared for it?",
      "Have you sought career advice or mentorship at UM, and what was your experience?",
      "What additional support or resources do you think could help alleviate your career-related stress?"
  ]
}


# UM-specific resource mapping (accurate links provided)
resource_map = {
  "Academics": "https://admissions.miami.edu/undergraduate/academics/academic-resources/index.html",
  "Mental Wellbeing": "https://health.miami.edu/counseling.html",
  "Physical Health": "https://health.miami.edu/herbert-wellness-center",
  "Social Life": "https://www.miami.edu/studentlife/",
  "Career Tension": "https://www.miami.edu/career/"
}


@app.route('/chat', methods=['POST'])
def chat():
  data = request.json
  user_input = data.get("message", "").strip()


  # Initialize conversation if not already started
  if "conversation" not in session:
      session["conversation"] = {
          "phase": "waiting_for_hello",  # phases: waiting_for_hello, domain_selection, domain_questions
          "domain": None,
          "domain_responses": [],
          "domain_step": 0
      }
      return jsonify({"message": WELCOME_MESSAGE})


  conv = session["conversation"]


  # Phase 1: Waiting for trigger ("hello")
  if conv["phase"] == "waiting_for_hello":
      if user_input.lower() == "hello":
          conv["phase"] = "domain_selection"
          return jsonify({"message": DOMAIN_SELECTION_QUESTION})
      else:
          return jsonify({"message": "Please type 'hello' to begin."})


  # Phase 2: Domain selection
  elif conv["phase"] == "domain_selection":
      if user_input not in domain_map:
          return jsonify({"message": f"⚠️ Invalid choice. {DOMAIN_SELECTION_QUESTION}"})
      conv["domain"] = user_input  # Store key ("1" to "5")
      conv["phase"] = "domain_questions"
      conv["domain_step"] = 0
      questions = domain_specific_questions[user_input]
      return jsonify({"message": questions[0]})


  # Phase 3: Asking domain-specific questions
  elif conv["phase"] == "domain_questions":
      domain = conv["domain"]
      questions = domain_specific_questions[domain]
      step = conv["domain_step"]


      conv["domain_responses"].append(user_input)


      if step < len(questions) - 1:
          conv["domain_step"] += 1
          next_question = questions[conv["domain_step"]]
          return jsonify({"message": next_question})
      else:
          result = analyze_stress(conv["domain"], conv["domain_responses"])
          session.pop("conversation", None)  # Reset the conversation after finishing
          return jsonify(result)


  return jsonify({"message": "An error occurred. Please try again."})


def analyze_stress(domain_key, responses):
  area = domain_map.get(domain_key, "Unknown")
  resource = resource_map.get(area, "Please consult university services for further support.")


  # Prepare a detailed prompt for OpenAI
  prompt = f"""
You are an expert mental wellness assistant for University of Miami students.
A student has provided the following detailed responses regarding their challenges in the area of {area}:
Responses:
{chr(10).join([f"{i+1}. {resp}" for i, resp in enumerate(responses)])}


Based on these responses, please provide a comprehensive, step-by-step plan that includes:
1. A brief analysis of the underlying issues causing their stress.
2. Specific actions they can take to address these challenges.
3. Detailed recommendations for UM resources (include the following specific resource for {area}: {resource}) and any steps to take.
4. Any additional advice or tips that would help them manage their stress effectively.


Return the output in the following JSON format:
{{
 "stress_area": "{area}",
 "detailed_plan": "<Your detailed plan here>"
}}
  """
  try:
      completion = openai.ChatCompletion.create(
          model="gpt-3.5-turbo",
          messages=[{"role": "system", "content": prompt}],
          temperature=0.7,
          max_tokens=500
      )
      advice_text = completion["choices"][0]["message"]["content"]
  except Exception as e:
      advice_text = (
          f"After reviewing your responses regarding {area}, it appears the key issues include {responses[0]}.\n"
          "Here is a suggested plan:\n"
          "1. Reflect on your main challenges and consider keeping a daily journal to identify stress triggers.\n"
          f"2. Schedule a meeting with the appropriate UM resource: {resource}.\n"
          "3. Consider joining a support group or workshop addressing your concerns.\n"
          "4. Establish a routine that includes stress-reduction activities like exercise or mindfulness.\n"
          "5. Follow up in a week to reassess and adjust your plan if needed."
      )
  return {"stress_area": area, "detailed_plan": advice_text}


@app.route('/reset', methods=['POST'])
def reset_chat():
  session.pop("conversation", None)
  return jsonify({"message": "Chat reset! Let's start fresh 😊"})


if __name__ == '__main__':
  app.run(debug=True, host="0.0.0.0", port=5000)

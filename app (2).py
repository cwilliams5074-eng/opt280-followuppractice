import streamlit as st
import anthropic
import os
import re
import json
from datetime import datetime

st.set_page_config(page_title="Follow-Up Interview Simulator", layout="centered")

MODEL = "claude-haiku-4-5-20251001"

# ── Visit context (shared by all patients) ──
VISIT_CONTEXT = """Visit type: contact lens follow-up evaluation.
Lens type: soft spherical, single vision.
Wearing modality: daily wear.
Replacement schedule: monthly.
Care system: multipurpose solution.
The patient was fit with trial lenses at a previous visit and is returning to report how they are doing.
Patient concerns involve some combination of comfort, vision, and/or lens care."""

# ── Rules every simulated patient follows ──
PATIENT_RULES = """You are role-playing a contact lens patient at a follow-up visit with an opticianry student. Stay in character at all times.

How to respond:
- Answer basic demographic questions (name, date of birth, occupation, phone, address) directly and cooperatively.
- Do not volunteer other information. Answer only what the student actually asks.
- If the student asks a broad, open-ended question (for example "How are the lenses doing?"), give a short, general answer that reflects your main impression, but hold back specific details until the student asks follow-up questions.
- If the student asks a specific question, answer it honestly and specifically.
- Details marked as hidden should only come out when the student asks a question that would reasonably lead a real patient to mention them.
- If asked something not covered in your profile, give a brief, realistic answer that is consistent with your profile. Do not invent new major problems or medical conditions.
- Speak like a real person, in plain everyday language. Do not use clinical jargon unless your profile says you would.
- Never give clinical advice, never act as the clinician, and never mention that you are an AI or that this is a simulation.
- Do not use stage directions, lists, or formatting. Do not use em dashes.
- Keep responses to 1 to 3 sentences."""

PATIENTS = {
    "Emily Torres, 24, retail store manager": {
        "initials": "ET",
        "greeting": "Hi! I'm here for my two-week contact lens check. I've really been enjoying them so far.",
        "profile": """You are Emily Torres, a 24-year-old retail store manager. Date of birth: March 14, 2002. This is your first time wearing contact lenses; before this you only wore glasses.

Trial lenses: Biofinity (CooperVision), base curve 8.6, diameter 14.0, -2.75 OD, -2.50 OS. You have worn them for two weeks. Care system: Opti-Free Puremoist multipurpose solution.

Personality: upbeat, friendly, and chatty about how much you love the lenses. You assume everything is going fine, so you answer lens care questions vaguely ("I just put them in the solution") until the student asks specifically how you do each step.

Comfort: very comfortable all day, no dryness or irritation.
Wearing time: put them in around 8 am, usually take them out around 7 pm (10 to 11 hours), but on long shifts sometimes 13 hours. You wear them 5 to 6 days a week. You have never slept in them.
Vision: clear at distance and near with the lenses. When you take the lenses out and put on your glasses, your vision is clear right away (no spectacle blur).

Hidden lens care details (only share when asked specifically about cleaning, storing, the case, or replacement):
- You do not rub the lenses. You just take them out and drop them in the case.
- You "top off" the old solution in the case with a little fresh solution instead of dumping it and refilling.
- When a lens fell out once and when you are in a hurry, you rinsed the lens with tap water.
- You keep the case on the bathroom counter next to the shower and have never replaced or air dried it. You close it with the lid while it is still wet.
- You think "monthly" means you can wear each pair for 30 wears, not 30 days, so you plan to keep them past a month if you skip days.""",
    },
    "Kevin Patel, 37, logistics supervisor": {
        "initials": "KP",
        "greeting": "Hey, I'm here for my contact lens follow-up. They're mostly fine, I just need to get my supply.",
        "profile": """You are Kevin Patel, a 37-year-old logistics supervisor at a distribution warehouse. Date of birth: January 9, 1989. You wore glasses for years and tried contacts briefly in college.

Trial lenses: Air Optix plus HydraGlyde (Alcon), base curve 8.6, diameter 14.2, -4.50 OD, -4.75 OS. You have worn them for two weeks. Care system: Biotrue multipurpose solution.

Personality: busy, matter-of-fact, and inclined to minimize problems ("it's fine, just a little dry"). You want to get your lenses and go. You give short answers until pressed.

Comfort: great in the morning, but by about 3 or 4 pm your eyes feel dry and scratchy, and they are sometimes red by the end of the day.
Hidden comfort detail: you have been using an over-the-counter "get the red out" eye drop (Visine) with the lenses in when they feel dry. Only share if asked whether you use any drops.
Wearing time: in at 5:30 am, out around 9 or 10 pm, so about 16 hours a day, 6 days a week.
Hidden wearing time details:
- You take 20 to 30 minute naps in your car on breaks a few times a week with the lenses in. Only share if asked about sleeping or napping in the lenses.
- You plan to wear each pair "as long as they still feel okay," probably 6 weeks or so. Only share if asked how often you replace them or about the replacement schedule.
Vision: clear with the lenses most of the day, a little hazy late in the day when they feel dry.
Spectacle blur (hidden, only share if asked about vision with glasses after removing lenses): when you take the lenses out at night and put your glasses on, everything is blurry for about 30 to 45 minutes. You assumed your glasses were just old.
Lens care: you rub and rinse each lens with Biotrue, use fresh solution each night, and rinse the case. This part is fine.""",
    },
    "Tyler Brooks, 21, college student": {
        "initials": "TB",
        "greeting": "Hi, I'm here for my one-week contacts check. They're okay I guess, but my vision is kind of weird sometimes.",
        "profile": """You are Tyler Brooks, a 21-year-old college student who also works part time as a barista. Date of birth: May 3, 2005. This is your first time wearing contact lenses.

Trial lenses: Total30 (Alcon), base curve 8.4, diameter 14.2, -1.50 OD, -3.25 OS. You have worn them for one week. Care system: renu Advanced Formula multipurpose solution.

Personality: casual and a little embarrassed about how hard handling has been. You give short answers like "it's fine I guess" and only open up when the student asks specific, nonjudgmental follow-up questions.

Comfort: usually comfortable. Occasionally a lens feels "edgy" and uncomfortable right after insertion.
Hidden handling details:
- When a lens feels edgy you take it out, and you have realized it was sometimes inside out. Only share if asked about insertion, handling, or why it feels edgy.
- Removal is hard. It takes you up to 10 minutes and you pinch a lot, and your eyes are a little red afterward. Only share if asked about removal.
Wearing time: about 8 to 10 hours a day, every day. You have never slept in them.
Vision: some days both eyes are crisp, but other days your left eye is blurry and you get a headache by the afternoon. It seems random to you.
Hidden vision detail: the R and L letters on your lens case have mostly worn off and you do not really check which lens goes in which eye. You do not realize your eyes have different prescriptions. Only share if asked how you keep track of which lens goes in which eye, or about the case.
Spectacle blur: none. Your glasses are clear right away after taking the lenses out.
Lens care: you use renu, sometimes rub the lenses and sometimes skip it when tired. You dump the old solution and use fresh each night.""",
    },
    "Denise Carter, 46, elementary school teacher": {
        "initials": "DC",
        "greeting": "Hello, I'm back for my two-week contact lens follow-up. Overall they're nice, but I have a question about my vision.",
        "profile": """You are Denise Carter, a 46-year-old third-grade teacher. Date of birth: September 30, 1980. You wore soft contact lenses in your twenties, stopped for years, and are trying them again. You are nearsighted and have worn single vision glasses.

Trial lenses: Acuvue Vita (Johnson & Johnson), base curve 8.4, diameter 14.0, -3.00 OD, -3.25 OS. You have worn them for two weeks. Care system: Biotrue multipurpose solution.

Personality: warm, polite, and detailed once asked, but a little worried something is wrong with the lenses. You wonder if they are "too strong."

Comfort: comfortable all day, no dryness.
Wearing time: about 9 to 10 hours on school days. You wear glasses on weekends. You have never slept in them.
Vision: distance vision is excellent, better than your glasses. Reading worksheets, grading papers, and reading your phone is harder, especially late in the day. Your eyes feel tired and you find yourself holding things farther away.
Hidden vision details:
- With your glasses, you have started taking them off or pushing them up to read up close, and that works well. Only share if asked how you read with your glasses or how near vision compares with your glasses.
- The near vision trouble is worse in dim light, like at a restaurant. Only share if asked about lighting or specific situations.
Spectacle blur: none. Glasses are clear right away after lens removal.
Lens care: you are careful. You rub and rinse each lens with Biotrue, use fresh solution every night, rinse the case and let it air dry, and you started a new case with the new lenses. You plan to replace the lenses monthly.""",
    },
    "Maria Santos, 33, hair stylist": {
        "initials": "MS",
        "greeting": "Hi, I'm here for my contact lens follow-up. They're okay, but they've been bothering me a little lately.",
        "profile": """You are Maria Santos, a 33-year-old hair stylist who works in a busy salon. Date of birth: February 18, 1993. You wore contact lenses for a short time several years ago and are trying them again.

Trial lenses: Bausch + Lomb ULTRA, base curve 8.5, diameter 14.2, -2.25 OD, -2.00 OS. You have worn them for two weeks. You were given a starter bottle of Biotrue multipurpose solution.

Personality: friendly and talkative about work and your clients, but a little defensive about cost. You do not mention the solution change unless asked specifically what solution you are using now.

Comfort: for the last week, the lenses sting and burn for the first few minutes after you put them in, then settle down. By mid afternoon your eyes feel scratchy and look a little red. The first week was totally fine.
Hidden comfort and care details:
- After the starter bottle ran out about a week ago, you switched to a cheaper store-brand multipurpose solution (you do not remember the name). The stinging started around then. Only share if asked what solution you are using now, whether anything changed, or when the stinging started.
- You put your lenses in after doing your own hair and makeup, including hairspray, and you do not always wash your hands first. When you do, you use a scented lotion hand soap. Only share if asked about hand washing or your routine before insertion.
Wearing time: about 11 to 12 hours a day, 5 days a week at the salon, where there are hairspray and chemical fumes. You have never slept in them.
Vision: clear in the morning. By late afternoon things look a little hazy or filmy, and blinking helps briefly.
Spectacle blur: none. Glasses are clear right away after lens removal.
Lens care: you rub and rinse the lenses and use fresh solution each night. You rinse the case with solution. You plan to replace the lenses monthly.""",
    },
}

COMPETENCY_ITEMS = [
    "Lens comfort: questioning about comfort at insertion, throughout the day, and at end of day, including dryness, irritation, redness, and use of any drops",
    "Wearing time: questioning about hours per day, days per week, and any sleeping or napping in lenses",
    "Quality of vision: questioning about distance and near vision, consistency or fluctuation, and specific visual tasks",
    "Spectacle blur: questioning about vision with glasses after lens removal",
    "Cleaning and disinfection procedures: questioning about solution used, rub and rinse steps, case care and replacement, handling and hygiene, and the lens replacement schedule",
    "Listening to and interpreting patient responses effectively: following up on concerns the patient raises, clarifying vague answers, and connecting related findings",
]

QUICK_PROMPTS = [
    "How have the lenses been feeling?",
    "How many hours a day are you wearing them?",
    "How is your vision with the lenses?",
    "How is your vision when you switch to your glasses?",
    "Can you walk me through how you clean and store your lenses?",
    "Have you had any problems since your last visit?",
]


def clean_dashes(text):
    """Keep student-facing text free of em dashes."""
    text = text.replace(" — ", ", ").replace("—", ", ")
    return text


def get_client():
    api_key = os.environ.get("ANTHROPIC_API_KEY") or st.secrets.get("ANTHROPIC_API_KEY")
    return anthropic.Anthropic(api_key=api_key)


def build_system_prompt(patient):
    return f"{PATIENT_RULES}\n\nVISIT CONTEXT\n{VISIT_CONTEXT}\n\nYOUR PATIENT PROFILE\n{patient['profile']}"


def get_ai_response(system_prompt, messages):
    client = get_client()
    response = client.messages.create(
        model=MODEL,
        max_tokens=300,
        system=system_prompt,
        messages=messages,
    )
    return clean_dashes(response.content[0].text)


def parse_feedback(raw):
    clean = raw.replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", clean, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
    return None


def get_feedback(messages, patient_name):
    client = get_client()
    patient = PATIENTS[patient_name]
    transcript = "\n".join(
        [f"{'Student' if m['role'] == 'user' else 'Patient'}: {m['content']}" for m in messages]
    )
    prompt = f"""You are an experienced opticianry clinical instructor reviewing a student's practice follow-up subjective interview with a contact lens patient. The patient was {patient_name}.

Visit context:
{VISIT_CONTEXT}

The patient's full background, including details the patient would only share if asked (for your reference only):
{patient['profile']}

Key areas a thorough follow-up subjective interview should cover:
{json.dumps(COMPETENCY_ITEMS, indent=2)}

Transcript:
{transcript}

Provide formative coaching feedback, not a score, grade, or pass/fail evaluation. Your feedback should help the student grow as a clinical interviewer. Speak directly to the student using "you." Consider not only which topics were covered, but whether the student listened to the patient's answers, followed up on concerns and vague responses, and uncovered the important details this patient had. If important details were never uncovered, you may point out what kind of questioning would have revealed them. Do not use em dashes.

Respond ONLY with valid JSON, no markdown or code blocks:
{{
  "explored_well": "<2-3 sentences identifying what the student did effectively in the interview>",
  "missed_or_thin": "<2-3 sentences identifying important areas that were missed entirely or not explored thoroughly enough>",
  "follow_up_suggestions": "<2-3 specific follow-up questions or interviewing considerations the student should keep in mind for next time>"
}}"""
    response = client.messages.create(
        model=MODEL,
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}],
    )
    fb = parse_feedback(response.content[0].text)
    if not fb:
        fb = {
            "explored_well": "Feedback could not be generated for this interview. Please review your transcript below.",
            "missed_or_thin": "Consider whether you explored comfort, wearing time, vision, spectacle blur, and lens care, and whether you followed up on what the patient told you.",
            "follow_up_suggestions": "You can download your transcript below, or start another patient encounter and try again.",
        }
    return {k: clean_dashes(str(fb.get(k, ""))) for k in ["explored_well", "missed_or_thin", "follow_up_suggestions"]}


def send_message(msg):
    patient = PATIENTS[st.session_state.selected_patient]
    st.session_state.messages.append({"role": "user", "content": msg})
    try:
        reply = get_ai_response(build_system_prompt(patient), st.session_state.messages)
    except Exception:
        st.session_state.messages.pop()
        st.error("The patient could not respond just now. Please try your question again.")
        return
    st.session_state.messages.append({"role": "assistant", "content": reply})
    st.session_state.feedback = None
    st.rerun()


def reset_session(patient_name=None):
    if patient_name:
        st.session_state.selected_patient = patient_name
    patient = PATIENTS[st.session_state.selected_patient]
    st.session_state.messages = [{"role": "assistant", "content": patient["greeting"]}]
    st.session_state.feedback = None
    st.session_state.interview_ended = False


# ── Session state init ──
if "selected_patient" not in st.session_state:
    st.session_state.selected_patient = list(PATIENTS.keys())[0]
    st.session_state.messages = []
    st.session_state.feedback = None
    st.session_state.interview_ended = False
    reset_session()

# ── UI ──
st.title("Follow-Up Interview Simulator")
st.markdown(
    "This patient is returning for a follow-up visit after wearing trial contact lenses. "
    "Approach this simulation as you would a real patient interview. Respond to what the patient tells you "
    "and use follow-up questions when appropriate. Practice using open-ended questions to encourage the patient "
    "to share information in their own words. There is no required script or checklist. Focus on having a "
    "natural clinical conversation."
)
st.markdown("---")

# ── Patient selector ──
st.markdown("**Select a patient**")
patient_name = st.selectbox(
    "Patient",
    list(PATIENTS.keys()),
    index=list(PATIENTS.keys()).index(st.session_state.selected_patient),
    label_visibility="collapsed",
)

if patient_name != st.session_state.selected_patient:
    reset_session(patient_name)
    st.rerun()

st.markdown("---")
st.markdown("**Patient interview**")

# ── Chat ──
for msg in st.session_state.messages:
    with st.chat_message("assistant" if msg["role"] == "assistant" else "user"):
        st.write(msg["content"])

# ── Input and prompts ──
if not st.session_state.interview_ended:
    st.markdown(" ")
    st.markdown("---")
    st.markdown("**Suggested questions**")
    cols = st.columns(2)
    for i, prompt_text in enumerate(QUICK_PROMPTS):
        if cols[i % 2].button(prompt_text, key=f"qp_{i}"):
            send_message(prompt_text)

    st.markdown("")
    if user_input := st.chat_input("Or type your own question…"):
        send_message(user_input)

    st.markdown("")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Start over", use_container_width=True):
            reset_session()
            st.rerun()
    with col2:
        if st.button("End interview & review feedback →", use_container_width=True, type="primary"):
            user_msgs = [m for m in st.session_state.messages if m["role"] == "user"]
            if len(user_msgs) < 3:
                st.warning("Continue your interview a little longer before reviewing feedback.")
            else:
                with st.spinner("Reviewing your interview…"):
                    try:
                        st.session_state.feedback = get_feedback(st.session_state.messages, patient_name)
                        st.session_state.interview_ended = True
                    except Exception:
                        st.error("Feedback could not be generated just now. Please try again.")
                if st.session_state.interview_ended:
                    st.rerun()

# ── Feedback and transcript ──
if st.session_state.interview_ended and st.session_state.feedback:
    fb = st.session_state.feedback
    st.markdown("---")
    st.subheader("Interview feedback")

    st.markdown("**What you explored effectively**")
    st.success(fb["explored_well"])

    st.markdown("**Areas that were missed or could be explored further**")
    st.warning(fb["missed_or_thin"])

    st.markdown("**Suggestions for follow-up questions and interviewing considerations**")
    st.info(fb["follow_up_suggestions"])

    st.markdown("---")
    st.markdown("**Interview transcript**")
    transcript = "\n\n".join([
        f"{'STUDENT' if m['role'] == 'user' else 'PATIENT'}: {m['content']}"
        for m in st.session_state.messages
    ])
    st.text_area("Transcript", transcript, height=300, label_visibility="collapsed")

    now = datetime.now().strftime("%B %d, %Y at %I:%M %p")
    exchanges = len([m for m in st.session_state.messages if m["role"] == "user"])
    download_text = f"""Follow-Up Interview Simulator
Patient: {patient_name}
Date: {now}
Exchanges: {exchanges}

INTERVIEW FEEDBACK

What you explored effectively:
{fb['explored_well']}

Areas that were missed or could be explored further:
{fb['missed_or_thin']}

Suggestions for follow-up questions and interviewing considerations:
{fb['follow_up_suggestions']}

TRANSCRIPT
{transcript}"""

    st.download_button(
        "Download transcript & feedback",
        data=download_text,
        file_name="followup-interview-transcript.txt",
        mime="text/plain",
        use_container_width=True,
    )

    st.markdown("")
    if st.button("Start another patient encounter →", use_container_width=True):
        reset_session()
        st.rerun()

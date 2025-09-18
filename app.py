from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    jsonify,
    flash,
)
import os
import json
from werkzeug.security import generate_password_hash, check_password_hash
import cv2
import numpy as np
from datetime import datetime
import requests
import base64
import re
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    login_required,
    logout_user,
    current_user,
)
import secrets

# Initialize Flask app
app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# MongoDB setup
app.config["MONGO_URI"] = "mongodb://localhost:27017/mental_health_app"
mongo = PyMongo(app)

# Login manager setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# API Key for chatbot (replace with your actual API key)
API_KEY = "your_api_key_here"


# User class for Flask-Login
class User(UserMixin):
    def __init__(self, user_data):
        self.id = str(user_data["_id"])
        self.email = user_data["email"]
        self.name = user_data["name"]
        self.profile_bio = user_data.get("profile_bio", "")
        self.join_date = user_data.get("join_date", datetime.utcnow())
        self.last_active = user_data.get("last_active", datetime.utcnow())

    def get_id(self):
        return self.id


@login_manager.user_loader
def load_user(user_id):
    user_data = mongo.db.users.find_one({"_id": ObjectId(user_id)})
    if user_data:
        return User(user_data)
    return None


# Routes
@app.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form.get("email")
        name = request.form.get("name")
        password = request.form.get("password")

        # Check if user already exists
        existing_user = mongo.db.users.find_one({"email": email})
        if existing_user:
            return render_template("register.html", error="Email already exists")

        # Create new user
        new_user = {
            "email": email,
            "name": name,
            "password": generate_password_hash(password, method="pbkdf2:sha256"),
            "profile_bio": "",
            "join_date": datetime.utcnow(),
            "last_active": datetime.utcnow(),
        }
        mongo.db.users.insert_one(new_user)

        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        user_data = mongo.db.users.find_one({"email": email})
        if not user_data or not check_password_hash(user_data["password"], password):
            return render_template("login.html", error="Invalid credentials")

        user = User(user_data)
        login_user(user)

        # Update last active timestamp
        mongo.db.users.update_one(
            {"_id": ObjectId(user.id)}, {"$set": {"last_active": datetime.utcnow()}}
        )

        return redirect(url_for("dashboard"))

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))


@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html", name=current_user.name)


@app.route("/chat")
@login_required
def chat():
    return render_template("chat.html", name=current_user.name)


@app.route("/cam")
@login_required
def cam():
    return render_template("cam.html", name=current_user.name)


@app.route("/process_chat", methods=["POST"])
@login_required
def process_chat():
    data = request.get_json()
    message = data.get("message", "")
    emotion = data.get("emotion", "")

    # Process the message based on emotion or direct input
    if emotion:
        response = get_chatbot_response(emotion)
    else:
        response = get_chatbot_response(message)

    return jsonify({"response": response})


@app.route("/process_emotion", methods=["POST"])
@login_required
def process_emotion():
    data = request.get_json()
    image_data = data.get("image")

    # Decode the base64 image
    image_data = re.sub("^data:image/.+;base64,", "", image_data)
    image_bytes = base64.b64decode(image_data)

    # Convert to numpy array for OpenCV
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    # Detect emotion using OpenCV
    detected_emotion = detect_emotion(img)

    # Get therapy suggestion based on detected emotion
    therapy = get_therapy_suggestion(detected_emotion)

    return jsonify({"emotion": detected_emotion, "therapy": therapy})


# Community Chat Routes
@app.route("/community")
@login_required
def community():
    """Display available chat rooms"""
    rooms = list(mongo.db.chat_rooms.find({"is_active": True}))

    # Get rooms that current user has joined
    joined_rooms = [
        doc["room_id"]
        for doc in mongo.db.room_members.find({"user_id": current_user.id})
    ]

    # Add joined status to each room
    for room in rooms:
        room["is_joined"] = str(room["_id"]) in joined_rooms

        # Count members in each room
        room["member_count"] = mongo.db.room_members.count_documents(
            {"room_id": str(room["_id"])}
        )

    return render_template("community.html", rooms=rooms, name=current_user.name)


@app.route("/community/room/<room_id>")
@login_required
def chat_room(room_id):
    """Display a specific chat room with messages"""
    room = mongo.db.chat_rooms.find_one({"_id": ObjectId(room_id)})
    if not room:
        flash("Room not found")
        return redirect(url_for("community"))

    # Check if user is a member
    is_member = mongo.db.room_members.find_one(
        {"room_id": room_id, "user_id": current_user.id}
    )

    # Get members for this room
    member_ids = [
        doc["user_id"] for doc in mongo.db.room_members.find({"room_id": room_id})
    ]
    members = []
    for member_id in member_ids:
        user_data = mongo.db.users.find_one({"_id": ObjectId(member_id)})
        if user_data:
            members.append({"id": member_id, "name": user_data["name"]})

    # Get messages for this room
    messages = list(mongo.db.messages.find({"room_id": room_id}).sort("timestamp", 1))

    # Get user details for each message
    for message in messages:
        user_data = mongo.db.users.find_one({"_id": ObjectId(message["user_id"])})
        if user_data:
            message["username"] = user_data["name"]
        else:
            message["username"] = "Unknown User"

    return render_template(
        "chat_room.html",
        room=room,
        messages=messages,
        members=members,
        is_member=bool(is_member),
        name=current_user.name,
    )


@app.route("/community/join/<room_id>")
@login_required
def join_room(room_id):
    """Join a chat room"""
    room = mongo.db.chat_rooms.find_one({"_id": ObjectId(room_id)})
    if not room:
        flash("Room not found")
        return redirect(url_for("community"))

    # Check if user is already a member
    existing_member = mongo.db.room_members.find_one(
        {"room_id": room_id, "user_id": current_user.id}
    )

    if not existing_member:
        # Add user to room members
        membership = {
            "room_id": room_id,
            "user_id": current_user.id,
            "joined_at": datetime.utcnow(),
        }
        mongo.db.room_members.insert_one(membership)
        flash(f"You've joined {room['name']}!")

    return redirect(url_for("chat_room", room_id=room_id))


@app.route("/community/leave/<room_id>")
@login_required
def leave_room(room_id):
    room = mongo.db.chat_rooms.find_one({"_id": ObjectId(room_id)})
    if not room:
        flash("Room not found")
        return redirect(url_for("community"))
    mongo.db.room_members.delete_one({"room_id": room_id, "user_id": current_user.id})

    flash(f"You've left {room['name']}.")
    return redirect(url_for("community"))


@app.route("/community/send_message", methods=["POST"])
@login_required
def send_message():
    """Process and save a new message"""
    if request.method == "POST":
        content = request.form.get("message")
        room_id = request.form.get("room_id")

        if content and room_id:
            # Check if user is a member of the room
            is_member = mongo.db.room_members.find_one(
                {"room_id": room_id, "user_id": current_user.id}
            )

            if not is_member:
                flash("You must join this room to send messages")
                return redirect(url_for("chat_room", room_id=room_id))

            new_message = {
                "content": content,
                "user_id": current_user.id,
                "room_id": room_id,
                "timestamp": datetime.utcnow(),
            }
            mongo.db.messages.insert_one(new_message)

            mongo.db.users.update_one(
                {"_id": ObjectId(current_user.id)},
                {"$set": {"last_active": datetime.utcnow()}},
            )
    return redirect(url_for("chat_room", room_id=room_id))

@app.route("/community/create_room", methods=["GET", "POST"])
@login_required
def create_room():
    """Create a new chat room"""
    if request.method == "POST":
        name = request.form.get("name")
        description = request.form.get("description")
        if name:
            new_room = {
                "name": name,
                "description": description,
                "created_at": datetime.utcnow(),
                "created_by": current_user.id,
                "is_active": True,
            }
            result = mongo.db.chat_rooms.insert_one(new_room)

            # Automatically add creator as a member
            membership = {
                "room_id": str(result.inserted_id),
                "user_id": current_user.id,
                "joined_at": datetime.utcnow(),
            }
            mongo.db.room_members.insert_one(membership)
            flash("Room created successfully!")
            return redirect(url_for("community"))
    return render_template("create_room.html", name=current_user.name)


@app.route("/profile")
@login_required
def profile():
    user_data = mongo.db.users.find_one({"_id": ObjectId(current_user.id)})
    if user_data:
        user = User(user_data)
        message_count = mongo.db.messages.count_documents({"user_id": current_user.id})
        return render_template("profile.html", user=user, message_count=message_count)
    return redirect(url_for("dashboard"))


@app.route("/profile/edit", methods=["GET", "POST"])
@login_required
def edit_profile():
    if request.method == "POST":
        name = request.form.get("name")
        bio = request.form.get("bio")

        mongo.db.users.update_one(
            {"_id": ObjectId(current_user.id)},
            {
                "$set": {
                    "name": name,
                    "profile_bio": bio,
                    "last_active": datetime.utcnow(),
                }
            },
        )
        flash("Profile updated successfully!")
        return redirect(url_for("profile"))

    user_data = mongo.db.users.find_one({"_id": ObjectId(current_user.id)})
    if user_data:
        user = User(user_data)
        return render_template("edit_profile.html", user=user)
    return redirect(url_for("dashboard"))

def get_chatbot_response(input_text):
    responses = {
        "happy": "I'm glad you're feeling happy! Would you like to share what's making you feel this way?",
        "sad": "I'm sorry to hear you're feeling sad. Would you like to talk about what's bothering you?",
        "angry": "I understand you're feeling angry. Taking deep breaths might help calm you down. Would you like to discuss what triggered this emotion?",
        "anxious": "It sounds like you're feeling anxious. Remember to breathe deeply. Would you like some techniques to help manage anxiety?",
        "neutral": "How are you feeling today? Would you like to talk about anything specific?",
    }

    for emotion, response in responses.items():
        if emotion.lower() in input_text.lower():
            return response

    try:
        # response = requests.post(
        #     "linkt",
        #     headers={"Authorization": f"Bearer {API_KEY}"},
        #     json={"message": input_text}
        # ).json()
        # return response["reply"]
        
        # sample text
        return "I'm here to support you. Can you tell me more about how you're feeling?"
    except Exception as e:
        print(f"API Error: {e}")
        return "I'm having trouble understanding. Could you rephrase that?"


def detect_emotion(image):

    # Convert to grayscale for face detection
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )

    # Detect faces
    faces = face_cascade.detectMultiScale(gray, 1.3, 5)

    # return neutral if no face detected,
    if len(faces) == 0:
        return "neutral"

    # Placeholder - in reality, you'd use a model like FER (Facial Emotion Recognition)
    # For this example, return a random emotion
    emotions = ["happy", "sad", "angry", "anxious", "neutral"]
    import random

    return random.choice(emotions)


def get_therapy_suggestion(emotion):
    """
    Suggest therapy based on detected emotion
    """
    therapy_suggestions = {
        "happy": [
            "Continue with positive activities that bring you joy.",
            "Practice gratitude journaling to maintain your positive mood.",
            "Consider sharing your positive energy through volunteer work.",
        ],
        "sad": [
            "Try gentle exercise like walking or yoga.",
            "Consider cognitive behavioral therapy techniques.",
            "Make sure to connect with supportive friends or family.",
            "Practice self-compassion exercises.",
        ],
        "angry": [
            "Practice deep breathing exercises for immediate relief.",
            "Try progressive muscle relaxation.",
            "Consider journaling about what triggered your anger.",
            "Physical activity can help release tension.",
        ],
        "anxious": [
            "Practice the 5-4-3-2-1 grounding technique.",
            "Try guided meditation or mindfulness exercises.",
            "Progressive muscle relaxation may help reduce physical tension.",
            "Consider limiting caffeine intake which can exacerbate anxiety.",
        ],
        "neutral": [
            "Practice mindfulness to become more aware of your emotions.",
            "Consider regular physical activity to promote overall well-being.",
            "Maintain social connections for emotional support.",
        ],
    }
    suggestions = therapy_suggestions.get(emotion, therapy_suggestions["neutral"])
    return suggestions


if __name__ == "__main__":
    app.run(debug=True)

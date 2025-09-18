# 🧠 Mental Health Support Chatbot

A smart and empathetic chatbot designed to provide **mental health support** by combining **emotion detection**, **AI-driven conversations**, and a **community platform** for peer interaction.  

---

## ✨ Features

- **😊 Emotion Detection**
  - Detects facial emotions using **OpenCV** and **deep learning models**.  
  - Provides **personalized recommendations** (e.g., relaxation tips, motivation, exercises).  

- **💬 AI Chat**
  - Chat with an **AI-powered assistant** built with Flask.  
  - Offers friendly, empathetic, and supportive conversations.  

- **🌍 Community Space**
  - MongoDB-powered community section for users to share experiences.  
  - Encourages **peer-to-peer mental health support**.  

---

## 🛠️ Tech Stack

- **Backend:** Flask (Python)  
- **Database:** MongoDB (via Flask-PyMongo)  
- **Authentication:** Flask-Login  
- **AI/ML:** OpenCV + NumPy for emotion detection  
- **APIs:** Requests (for fetching resources/recommendations)  

---

## 🚀 Getting Started

### 1. Clone the repository
```bash
git clone https://github.com/your-username/mental-health-chatbot.git
cd mental-health-chatbot
```

### 2. Create a virtual environment
```bash
python -m venv venv
source venv/bin/activate   # On Linux/Mac
venv\Scripts\activate      # On Windows
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the project
```bash
python app.py
```

The server will start at:  
👉 `http://127.0.0.1:5000/`

---

## 📦 Requirements

Your `requirements.txt` includes:  

```
Flask==2.0.1
Werkzeug==2.0.1
flask-pymongo==2.3.0
Flask-Login==0.5.0
opencv-python-headless>=4.5.3
numpy>=1.21.0
requests==2.26.0
```

---

## ⚠️ Disclaimer
This chatbot is **not a replacement for professional mental health services**.  
If you are struggling with serious mental health issues, please consult a **licensed professional or helpline** in your area.  

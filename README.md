# Content Room 🚀

A modern, AI-powered platform for content creators offering a beautiful frontend and a robust backend to handle content generation, scheduling, moderation, and competitor intelligence.

---

## 🏗️ Architecture
Content Room is split into two primary components:
1. **[Frontend](./Frontend/README.md)**: A sleek, responsive React + TypeScript web application built with Vite, TailwindCSS, and shadcn/ui.
2. **[Backend](./Backend/README.md)**: A high-performance Python FastAPI service featuring asynchronous database access and comprehensive AI service integrations.

---

## ✨ Key Features
- **Creator Studio**: Multi-modal AI generation tools including smart captions, summaries, hashtag generation, tone rewriting, and translation.
- **Competitor Intelligence**: Analyze competitor content from any public URL and identify strategic content gaps.
- **Content Calendar**: Generate full monthly publishing plans tailored directly to your specific niche.
- **Advanced Content Moderation**: Comprehensive Text, Image, Audio, and Video moderation powered primarily by AWS Rekognition with robust local fallbacks.
- **Cross-Platform Scheduling**: Plan and automatically execute pre-publish safe checks for Twitter, LinkedIn, and Instagram.
- **Flexible Authentication**: JWT-based session management secured by Argon2. Most core features operate fully smoothly without requiring users to log in!

---

## 🚀 Quick Start Guide

You will need to run the backend API and the frontend application simultaneously. 

### 1. Backend Setup (Port 8000)
```bash
# Navigate to the Backend folder
cd Backend

# Install Python requirements
pip install -r requirements.txt

# Configure your environment
# (Ensure your .env contains necessary AWS/LLM credentials)
cp .env.example .env

# Start the development server
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```
*API Docs available at: http://localhost:8000/docs*

### 2. Frontend Setup (Port 5173 / 8080)
```bash
# Open a new terminal and navigate to the Frontend folder
cd Frontend

# Install Node dependencies
npm install  # or: yarn install

# Setup environment variables
echo "VITE_API_BASE_URL=http://localhost:8000" > .env

# Start the Vite development server
npm run dev
```
*Frontend available at: http://localhost:5173 (or as displayed in your terminal)*

---

## 🛠️ Tech Stack Overview

### Frontend
- **Core**: React 18, TypeScript, Vite, React Router v6
- **Styling**: TailwindCSS, shadcn/ui, Lucide React
- **State Management & Forms**: React Query, React Hook Form, Zod

### Backend
- **Core**: Python 3.10+, FastAPI, Uvicorn
- **Database**: PostgreSQL (via `asyncpg`) for Production / SQLite (via `aiosqlite`) for Development; managed with SQLAlchemy ORM
- **Security & Auth**: Argon2 hashing, python-jose (JWT)
- **AI Integrations**: AWS Bedrock & Rekognition (Primary), OpenAI / Groq / OpenRouter (Fallbacks)

---

## 📖 Complete Documentation

For detailed configurations, deployment structures, testing workflows, and API specifics, please refer to the dedicated README files in each directory:
- 🎨 **[Frontend README](./Frontend/README.md)**
- 🔧 **[Backend README](./Backend/README.md)**

---

**License:** MIT License

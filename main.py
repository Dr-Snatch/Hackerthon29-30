"""
Adaptive Lecture Summarizer - Backend API
==========================================

Project: Adaptive learning platform that generates personalized lecture summaries
File: main.py
Purpose: FastAPI backend with streaming summaries, quiz generation, and answer evaluation

Features:
- 5-level adaptive summaries (Complete Beginner to Expert)
- Real-time streaming with Server-Sent Events (SSE)
- Natural language quiz generation
- AI-powered answer evaluation
- Uses Claude Haiku 4 for summaries (speed), Sonnet 4.5 for quiz/evaluation (quality)

Architecture:
- FastAPI for REST API and SSE streaming
- Anthropic Claude API for AI generation
- Jinja2 templates for HTML rendering
- Separate static files for CSS/JS

Dependencies:
- fastapi: Web framework
- anthropic: Claude API client
- uvicorn: ASGI server
- jinja2: Template engine
- python-dotenv: Environment variable management

Environment Variables Required:
- ANTHROPIC_API_KEY: Your Anthropic API key

Author: Hackathon Team
Date: November 2025
"""

import os
import uuid
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Form, HTTPException, Request, UploadFile, File, Cookie, Response
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from fastapi.middleware.cors import CORSMiddleware
import anthropic
from dotenv import load_dotenv

# Import file upload modules
from config import config, WhisperMode
from file_utils import FileValidator
from pdf_extractor import PDFExtractor
from document_extractor import DocumentExtractor
from audio_transcription import transcriber

# Load environment variables
load_dotenv()

# Initialize API clients
anthropic_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# Initialize FastAPI app
app = FastAPI(title="Adaptive Lecture Summarizer")

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

from fastapi.responses import StreamingResponse
import json as json_module

import asyncio

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Session-based memory storage (in production, use Redis or database)
# Key: session_id, Value: {"sources": [], "combined_text": ""}
lecture_memory = {}

def generate_quiz(transcript: str, knowledge_level: int) -> list:
    """
    Generate natural language quiz questions based on knowledge level
    Returns list of questions
    """
    level_descriptions = {
        0: "complete beginner with no prior knowledge",
        1: "beginner with basic familiarity",
        2: "intermediate learner with solid foundation",
        3: "advanced learner with strong background",
        4: "expert with deep technical knowledge"
    }

    try:
        print(f"Generating quiz for level {knowledge_level}...")
        message = anthropic_client.messages.create(
            model="claude-sonnet-4-5-20250929",  # Keep Sonnet for quiz quality
            max_tokens=2000,
            messages=[{
                "role": "user",
                "content": f"""Based on this lecture transcript, create 4 natural language quiz questions for a {level_descriptions[knowledge_level]}.

These questions should:
- Be open-ended (require explanation, not yes/no)
- Test understanding at the appropriate depth for this level
- Encourage critical thinking
- Be answerable based on the lecture content

Transcript:
{transcript}

Format your response as a JSON array of questions ONLY, like this:
[
  "Question 1 text here?",
  "Question 2 text here?",
  "Question 3 text here?",
  "Question 4 text here?"
]

Return ONLY the JSON array, no other text."""
            }]
        )

        response_text = message.content[0].text.strip()
        print("Quiz generated successfully!")
        print(f"Raw response: {response_text[:200]}...")

        # Remove markdown code blocks if present
        if response_text.startswith('```'):
            # Remove ```json and ``` markers
            response_text = response_text.replace('```json', '').replace('```', '').strip()

        # Parse JSON response
        import json
        questions = json.loads(response_text)

        return questions

    except Exception as e:
        print(f"Quiz generation error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Quiz generation failed: {str(e)}")


def generate_single_question(transcript: str, difficulty_level: int, previous_questions: list = None) -> str:
    """
    Generate a single question at specific difficulty level for adaptive quiz
    Returns a single question string
    """
    level_descriptions = {
        0: ("complete beginner", "basic recall and simple concepts"),
        1: ("beginner", "fundamental understanding and basic application"),
        2: ("intermediate", "connecting concepts and practical application"),
        3: ("advanced", "deep analysis and nuanced understanding"),
        4: ("expert", "critical evaluation and expert-level insights")
    }

    level_name, level_focus = level_descriptions[difficulty_level]

    try:
        print(f"Generating question at difficulty level {difficulty_level} ({level_name})...")

        # Build context about previous questions to avoid repetition
        previous_context = ""
        if previous_questions:
            previous_context = f"\n\nPrevious questions already asked:\n" + "\n".join([f"- {q}" for q in previous_questions])
            previous_context += "\n\nMake sure this question tests a DIFFERENT concept or aspect of the content."

        message = anthropic_client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=500,
            messages=[{
                "role": "user",
                "content": f"""Based on this lecture transcript, create ONE open-ended quiz question for a {level_name} level learner.

Difficulty Level: {difficulty_level}/4 (0=easiest, 4=hardest)
Focus: {level_focus}

Transcript:
{transcript}
{previous_context}

The question should:
- Be open-ended (require explanation, not yes/no)
- Test {level_focus}
- Be answerable based on the lecture content
- Be at exactly difficulty level {difficulty_level}

Return ONLY the question text, nothing else."""
            }]
        )

        question = message.content[0].text.strip()
        print(f"Generated level {difficulty_level} question: {question[:100]}...")

        return question

    except Exception as e:
        print(f"Question generation error: {str(e)}")
        raise Exception(f"Question generation failed: {str(e)}")


def evaluate_answer(question: str, user_answer: str, transcript: str, knowledge_level: int) -> dict:
    """
    Evaluate a user's natural language answer to a quiz question
    Returns feedback and assessment
    """
    import json
    import re

    level_guidance = {
        0: {
            "name": "complete beginner",
            "tone": "extremely encouraging and patient",
            "depth": "Explain concepts using simple analogies. Celebrate effort and progress. Provide gentle guidance without overwhelming.",
            "criteria": "Look for basic understanding of core concepts, even if terminology isn't perfect."
        },
        1: {
            "name": "beginner",
            "tone": "supportive and clear",
            "depth": "Build confidence while introducing proper terminology. Explain why misconceptions occur.",
            "criteria": "Expect foundational understanding with some technical terms, but allow for informal explanations."
        },
        2: {
            "name": "intermediate",
            "tone": "constructive and detailed",
            "depth": "Connect concepts to broader context. Point out nuances they might have missed.",
            "criteria": "Expect proper use of terminology and ability to connect related concepts."
        },
        3: {
            "name": "advanced",
            "tone": "analytical and thought-provoking",
            "depth": "Discuss implications and edge cases. Challenge them to think deeper about assumptions.",
            "criteria": "Expect sophisticated understanding, nuanced analysis, and awareness of limitations."
        },
        4: {
            "name": "expert",
            "tone": "collegial and rigorous",
            "depth": "Engage with technical precision. Discuss research implications and novel insights.",
            "criteria": "Expect mastery-level analysis, critical evaluation, and identification of what's significant or novel."
        }
    }

    level_info = level_guidance.get(knowledge_level, level_guidance[2])

    try:
        print(f"Evaluating answer for level {knowledge_level}...", flush=True)
        message = anthropic_client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=400,
            messages=[{
                "role": "user",
                "content": f"""Evaluate this answer briefly and constructively.

**Question:** {question}

**Student's Answer:** {user_answer}

**Reference Content:**
{transcript[:3000]}

**Evaluation Guidelines:**
- Keep feedback under 50 words
- Be {level_info['tone']}
- If correct: Confirm + 1 key insight
- If partial: Point out what's right + 1 key missing piece
- If incorrect: Briefly clarify the correct concept

**Scoring:**
- "correct": Strong understanding (minor details may be missing)
- "partial": Partial understanding with gaps
- "incorrect": Major misunderstanding

Return ONLY JSON:
{{
  "score": "correct|partial|incorrect",
  "feedback": "Your concise feedback (under 50 words)"
}}"""
            }]
        )

        print("API call successful, processing response...", flush=True)

        # Get response text
        response_text = message.content[0].text.strip()
        print(f"Raw response length: {len(response_text)}", flush=True)
        print(f"Raw response first 200 chars: {response_text[:200]}", flush=True)

        # Remove markdown code blocks if present
        if '```' in response_text:
            print("Detected code block markers, extracting JSON...", flush=True)
            # Try to find JSON block
            json_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', response_text, re.DOTALL)
            if json_match:
                response_text = json_match.group(1).strip()
                print("Extracted JSON from code block", flush=True)
            else:
                # If no match, just remove all lines with ```
                lines = response_text.split('\n')
                lines = [line for line in lines if '```' not in line]
                response_text = '\n'.join(lines).strip()
                print("Removed code block markers manually", flush=True)

        print(f"Cleaned response length: {len(response_text)}", flush=True)
        print(f"Cleaned response: {response_text}", flush=True)

        # Parse JSON response
        if not response_text:
            raise ValueError("Response text is empty after cleaning")

        evaluation = json.loads(response_text)
        print(f"JSON parsed successfully: {evaluation}", flush=True)

        return evaluation
        
    except Exception as e:
        print(f"Answer evaluation error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Answer evaluation failed: {str(e)}")


async def generate_all_summaries_stream(transcript: str, language: str = 'en', knowledge_level: float = 0.0):
    """
    Generate summaries starting from user's current knowledge level
    """
    try:
        # Convert knowledge level (0.0-1.0) to level index (0-4)
        start_level = min(4, int(knowledge_level * 5))
        print(f"Starting streaming summary generation in {language} from level {start_level}...")

        # Language mapping
        language_names = {
            'en': 'English',
            'es': 'Spanish',
            'fr': 'French',
            'de': 'German',
            'zh': 'Chinese',
            'ja': 'Japanese',
            'ar': 'Arabic',
            'hi': 'Hindi',
            'pt': 'Portuguese',
            'ru': 'Russian'
        }

        language_instruction = f"Respond in {language_names.get(language, 'English')}." if language != 'en' else ""

        # Send initial test message
        yield f"data: {json_module.dumps({'type': 'test', 'message': 'Stream started'})}\n\n"

        level_descriptions = [
            {
                "label": "COMPLETE BEGINNER (0.0-0.2)",
                "audience": "someone with absolutely no prior knowledge of this topic",
                "approach": "Start with the absolute basics. Define every technical term using simple, everyday language. Use relatable analogies and real-world examples.",
                "language_style": "conversational and patient",
                "depth": "Focus on 'what' and 'why' before 'how'. Break down complex ideas into digestible pieces.",
                "avoid": "jargon, acronyms without explanation, assumptions about prior knowledge"
            },
            {
                "label": "BEGINNER (0.2-0.4)",
                "audience": "someone with basic familiarity who wants to build a stronger foundation",
                "approach": "Introduce proper terminology while still providing clear explanations. Connect new concepts to familiar ones.",
                "language_style": "clear and supportive",
                "depth": "Explain both 'what' and 'why', with some introduction to 'how'. Use examples to reinforce understanding.",
                "avoid": "overly technical details, advanced edge cases"
            },
            {
                "label": "INTERMEDIATE (0.4-0.6)",
                "audience": "someone with solid foundational knowledge seeking deeper understanding",
                "approach": "Use standard technical terminology. Show how concepts connect and build upon each other. Include practical applications.",
                "language_style": "professional and informative",
                "depth": "Balance 'what', 'why', and 'how'. Discuss practical implications and use cases.",
                "avoid": "over-simplification, repetition of basic concepts"
            },
            {
                "label": "ADVANCED (0.6-0.8)",
                "audience": "someone with strong technical background seeking nuanced insights",
                "approach": "Use advanced terminology freely. Discuss nuances, trade-offs, and edge cases. Explore implications and connections to related concepts.",
                "language_style": "analytical and detailed",
                "depth": "Emphasize 'how' and 'why'. Discuss limitations, alternatives, and deeper implications.",
                "avoid": "over-explaining basics, surface-level descriptions"
            },
            {
                "label": "EXPERT (0.8-1.0)",
                "audience": "someone with expert-level knowledge seeking cutting-edge insights",
                "approach": "Be concise and information-dense. Focus on what's novel, significant, or non-obvious. Discuss research implications and future directions.",
                "language_style": "rigorous and precise",
                "depth": "Dive deep into advanced implications, research frontiers, and sophisticated analysis.",
                "avoid": "basic explanations, redundant information"
            }
        ]

        # Generate from user's level onwards
        for level in range(start_level, 5):
            level_info = level_descriptions[level]

            yield f"data: {json_module.dumps({'type': 'level_start', 'level': level})}\n\n"

            with anthropic_client.messages.stream(
                model="claude-sonnet-4-5-20250929",  # Using Sonnet - Haiku 4 not available yet
                max_tokens=1500,
                messages=[{
                    "role": "user",
                    "content": f"""{language_instruction}

You are creating a lecture summary for **{level_info['audience']}**.

**Level:** {level_info['label']}

**Your Approach:**
{level_info['approach']}

**Language Style:** {level_info['language_style']}
**Depth:** {level_info['depth']}
**Avoid:** {level_info['avoid']}

**Lecture Transcript:**
{transcript}

**Structure your summary with these sections:**

## Key Concepts
Identify and explain the main ideas at the appropriate depth for this level.

## Core Takeaways
What should the learner remember and understand from this lecture?

## Important Details
Relevant specifics, examples, or technical information suited to this level.

## Suggested Focus Areas
What should they study or practice to deepen their understanding?

Remember: Tailor every explanation to {level_info['audience']}. {level_info['approach']}"""
                }]
            ) as stream:
                for text in stream.text_stream:
                    yield f"data: {json_module.dumps({'type': 'content', 'text': text, 'level': level})}\n\n"

        # Send completion event
        yield f"data: {json_module.dumps({'type': 'complete'})}\n\n"
        print("Streaming complete!")

    except Exception as e:
        error_data = json_module.dumps({'type': 'error', 'message': str(e)})
        yield f"data: {error_data}\n\n"
        print(f"Streaming error: {str(e)}")


def generate_all_summaries(transcript: str) -> dict:
    """
    Generate 5 adaptive summaries with streaming
    Yields chunks as they're generated
    """
    try:
        print("Starting streaming summary generation...")
        
        # Send initial test message
        yield f"data: {json_module.dumps({'type': 'test', 'message': 'Stream started'})}\n\n"
        
        # Track which level we're currently receiving
        current_level = None
        buffer = ""
        
        with anthropic_client.messages.stream(
            model="claude-sonnet-4-5-20250929",
            max_tokens=8000,
            messages=[{
                "role": "user",
                "content": f"""Create 5 different summaries of this lecture transcript, each adapted to a different knowledge level. Each summary should be DISTINCTLY DIFFERENT and avoid repeating information unnecessarily.

**LEVEL 0 - COMPLETE BEGINNER (0.0-0.2)**
Assumes absolutely no prior knowledge. Define every technical term in simple language. Use everyday analogies. Build from first principles. Be patient and thorough.

**LEVEL 1 - BEGINNER (0.2-0.4)**  
Assumes basic familiarity with the topic area. Still explain technical terms but can assume some foundational concepts. Use clear examples.

**LEVEL 2 - INTERMEDIATE (0.4-0.6)**
Assumes solid foundational knowledge. Use standard technical terminology. Focus on connections between concepts and practical applications.

**LEVEL 3 - ADVANCED (0.6-0.8)**
Assumes strong technical background. Use advanced terminology freely. Focus on nuances, implications, and deeper understanding.

**LEVEL 4 - EXPERT (0.8-1.0)**
Assumes expert-level knowledge. Be concise and dense. Focus on cutting-edge insights, edge cases, research implications, and what's novel or significant.

Transcript:
{transcript}

For EACH level, provide:
## Key Concepts
## Core Takeaways  
## Important Details
## Suggested Focus Areas

Format your response EXACTLY like this:
---LEVEL_0---
[Complete beginner summary with ## section headers]

---LEVEL_1---
[Beginner summary with ## section headers]

---LEVEL_2---
[Intermediate summary with ## section headers]

---LEVEL_3---
[Advanced summary with ## section headers]

---LEVEL_4---
[Expert summary with ## section headers]"""
            }]
        ) as stream:
            for text in stream.text_stream:
                buffer += text
                
                # Check if we hit a level marker
                if '---LEVEL_' in buffer:
                    # Extract level number
                    parts = buffer.split('---LEVEL_')
                    if len(parts) > 1:
                        level_part = parts[-1].split('---')[0]
                        if level_part.strip().isdigit():
                            new_level = level_part.strip()
                            if new_level != current_level:
                                current_level = new_level
                                # Send level change event
                                yield f"data: {json_module.dumps({'type': 'level_start', 'level': current_level})}\n\n"
                
                # Send the text chunk
                yield f"data: {json_module.dumps({'type': 'content', 'text': text, 'level': current_level})}\n\n"
        
        # Send completion event
        yield f"data: {json_module.dumps({'type': 'complete'})}\n\n"
        print("Streaming complete!")
        
    except Exception as e:
        error_data = json_module.dumps({'type': 'error', 'message': str(e)})
        yield f"data: {error_data}\n\n"
        print(f"Streaming error: {str(e)}")


def generate_all_summaries(transcript: str) -> dict:
    """
    Generate 5 adaptive summaries at once (one API call)
    Returns dict with levels 0, 1, 2, 3, 4 as keys
    """
    try:
        print("Generating 5-level adaptive summaries...")
        message = anthropic_client.messages.create(
            model="claude-sonnet-4-5-20250929",  # Most advanced model available
            max_tokens=8000,
            messages=[{
                "role": "user",
                "content": f"""Create 5 different summaries of this lecture transcript, each adapted to a different knowledge level. Each summary should be DISTINCTLY DIFFERENT and avoid repeating information unnecessarily.

**LEVEL 0 - COMPLETE BEGINNER (0.0-0.2)**
Assumes absolutely no prior knowledge. Define every technical term in simple language. Use everyday analogies. Build from first principles. Be patient and thorough.

**LEVEL 1 - BEGINNER (0.2-0.4)**  
Assumes basic familiarity with the topic area. Still explain technical terms but can assume some foundational concepts. Use clear examples.

**LEVEL 2 - INTERMEDIATE (0.4-0.6)**
Assumes solid foundational knowledge. Use standard technical terminology. Focus on connections between concepts and practical applications.

**LEVEL 3 - ADVANCED (0.6-0.8)**
Assumes strong technical background. Use advanced terminology freely. Focus on nuances, implications, and deeper understanding.

**LEVEL 4 - EXPERT (0.8-1.0)**
Assumes expert-level knowledge. Be concise and dense. Focus on cutting-edge insights, edge cases, research implications, and what's novel or significant.

Transcript:
{transcript}

For EACH level, provide:
## Key Concepts
## Core Takeaways  
## Important Details
## Suggested Focus Areas

Format your response EXACTLY like this:
---LEVEL_0---
[Complete beginner summary with ## section headers]

---LEVEL_1---
[Beginner summary with ## section headers]

---LEVEL_2---
[Intermediate summary with ## section headers]

---LEVEL_3---
[Advanced summary with ## section headers]

---LEVEL_4---
[Expert summary with ## section headers]"""
            }]
        )
        
        full_response = message.content[0].text
        print("All summaries generated successfully!")
        print(f"Response length: {len(full_response)} characters")
        
        # Debug: Print first 500 chars to see format
        print("Response preview:", full_response[:500])
        
        # Parse the response into 5 separate summaries
        summaries = {}
        parts = full_response.split('---LEVEL_')
        
        print(f"Split into {len(parts)} parts")
        
        for i, part in enumerate(parts[1:]):  # Skip the first empty split
            if not part.strip():
                print(f"Part {i} is empty, skipping")
                continue
            lines = part.strip().split('\n', 1)
            if len(lines) < 2:
                print(f"Part {i} has insufficient lines, skipping")
                continue
            level_num = lines[0].replace('---', '').strip()
            summary_content = lines[1].strip()
            summaries[level_num] = summary_content
            print(f"Parsed level {level_num}, length: {len(summary_content)} chars")
        
        # Ensure we have all 5 levels
        if len(summaries) != 5:
            print(f"Warning: Expected 5 summaries, got {len(summaries)}")
            print(f"Available keys: {list(summaries.keys())}")
        
        return summaries
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Summary generation failed: {str(e)}")
    """
    Generate natural language quiz questions based on knowledge level
    Returns list of questions
    """
    level_descriptions = {
        0: "complete beginner with no prior knowledge",
        1: "beginner with basic familiarity",
        2: "intermediate learner with solid foundation",
        3: "advanced learner with strong background",
        4: "expert with deep technical knowledge"
    }
    
    try:
        print(f"Generating quiz for level {knowledge_level}...")
        message = anthropic_client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=2000,
            messages=[{
                "role": "user",
                "content": f"""Based on this lecture transcript, create 4 natural language quiz questions for a {level_descriptions[knowledge_level]}.

These questions should:
- Be open-ended (require explanation, not yes/no)
- Test understanding at the appropriate depth for this level
- Encourage critical thinking
- Be answerable based on the lecture content

Transcript:
{transcript}

Format your response as a JSON array of questions ONLY, like this:
[
  "Question 1 text here?",
  "Question 2 text here?",
  "Question 3 text here?",
  "Question 4 text here?"
]

Return ONLY the JSON array, no other text."""
            }]
        )
        
        response_text = message.content[0].text.strip()
        print("Quiz generated successfully!")
        
        # Parse JSON response
        import json
        questions = json.loads(response_text)
        
        return questions
        
    except Exception as e:
        print(f"Quiz generation error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Quiz generation failed: {str(e)}")


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """
    Serve the main HTML interface
    """
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/process_stream")
async def process_lecture_stream(
    request: Request,
    session_id: Optional[str] = Cookie(default=None)
):
    """
    Process lecture transcript and stream adaptive summaries starting from user's level
    Supports both direct transcript input and memory-based content
    """
    try:
        body = await request.json()
        use_memory = body.get('use_memory', False)
        language = body.get('language', 'en')
        knowledge_level = body.get('knowledge_level', 0.0)  # Get user's current level

        # Check for session_id in request body first, then fall back to cookie
        if not session_id:
            session_id = body.get('session_id')

        # Get transcript from memory or request body
        if use_memory:
            if not session_id or session_id not in lecture_memory:
                print(f"Session check - ID: {session_id}, In memory: {session_id in lecture_memory if session_id else False}")
                print(f"Available sessions: {list(lecture_memory.keys())}")
                raise HTTPException(status_code=400, detail="No memory found. Please add sources first.")

            transcript = lecture_memory[session_id]["combined_text"]
            if not transcript or len(transcript.strip()) < 50:
                raise HTTPException(status_code=400, detail="Memory is empty. Please add sources first.")
        else:
            transcript = body.get('transcript', '')
            # Validate transcript
            if not transcript or len(transcript.strip()) < 50:
                raise HTTPException(status_code=400, detail="Transcript must be at least 50 characters")

        async def safe_stream_wrapper():
            """Wrapper to handle disconnection gracefully"""
            try:
                async for chunk in generate_all_summaries_stream(transcript, language, knowledge_level):
                    # Check if client is still connected
                    if await request.is_disconnected():
                        print("Client disconnected, stopping stream")
                        break
                    yield chunk
            except Exception as e:
                import traceback
                error_details = traceback.format_exc()
                print(f"Stream error: {str(e)}")
                print(f"Stream error traceback:\n{error_details}")
                # Try to send error to client if still connected
                if not await request.is_disconnected():
                    error_message = str(e) if str(e) else "An error occurred while generating the summary"
                    error_data = {'type': 'error', 'message': error_message}
                    yield f"data: {json_module.dumps(error_data)}\n\n"

        return StreamingResponse(
            safe_stream_wrapper(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            }
        )
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Streaming error: {str(e)}")
        print(f"Full traceback:\n{error_details}")
        raise HTTPException(status_code=500, detail=str(e) if str(e) else "Internal server error")

@app.post("/process")
async def process_lecture(
    transcript: str = Form(...)
):
    """
    Process lecture transcript and generate all 5 adaptive summaries at once
    """
    # Validate transcript
    if not transcript or len(transcript.strip()) < 50:
        raise HTTPException(status_code=400, detail="Transcript must be at least 50 characters")
    
    try:
        # Generate all 5 summaries in one API call
        summaries = generate_all_summaries(transcript)
        
        return JSONResponse({
            "success": True,
            "summaries": summaries,
            "transcript_length": len(transcript)
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate_quiz")
async def create_quiz(
    transcript: str = Form(...),
    knowledge_level: int = Form(...)
):
    """
    Generate quiz questions based on transcript and knowledge level
    """
    if not 0 <= knowledge_level <= 4:
        raise HTTPException(status_code=400, detail="Knowledge level must be between 0 and 4")
    
    if not transcript or len(transcript.strip()) < 50:
        raise HTTPException(status_code=400, detail="Transcript must be at least 50 characters")
    
    try:
        questions = generate_quiz(transcript, knowledge_level)
        
        return JSONResponse({
            "success": True,
            "questions": questions,
            "knowledge_level": knowledge_level
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate_adaptive_question")
async def create_adaptive_question(
    request: Request,
    session_id: Optional[str] = Cookie(default=None)
):
    """
    Generate a single question at specific difficulty for adaptive quiz
    Supports both direct transcript input and memory-based content
    """
    try:
        body = await request.json()
        use_memory = body.get('use_memory', False)
        difficulty_level = body.get('difficulty_level', 0)
        previous_questions = body.get('previous_questions', [])

        if not 0 <= difficulty_level <= 4:
            raise HTTPException(status_code=400, detail="Difficulty level must be between 0 and 4")

        # Check for session_id in request body first, then fall back to cookie
        if not session_id:
            session_id = body.get('session_id')

        # Get transcript from memory or request body
        if use_memory:
            if not session_id or session_id not in lecture_memory:
                raise HTTPException(status_code=400, detail="No memory found. Please add sources first.")

            transcript = lecture_memory[session_id]["combined_text"]
            if not transcript or len(transcript.strip()) < 50:
                raise HTTPException(status_code=400, detail="Memory is empty. Please add sources first.")
        else:
            transcript = body.get('transcript', '')
            if not transcript or len(transcript.strip()) < 50:
                raise HTTPException(status_code=400, detail="Transcript must be at least 50 characters")

        question = generate_single_question(transcript, difficulty_level, previous_questions)

        return JSONResponse({
            "success": True,
            "question": question,
            "difficulty_level": difficulty_level
        })

    except Exception as e:
        print(f"Error in generate_adaptive_question endpoint: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/evaluate_answer")
async def check_answer(
    question: str = Form(...),
    answer: str = Form(...),
    knowledge_level: int = Form(...),
    transcript: str = Form(default=''),
    use_memory: str = Form(default='false'),
    session_id: Optional[str] = Form(default=None),
    cookie_session_id: Optional[str] = Cookie(default=None, alias="session_id")
):
    """
    Evaluate a user's answer to a quiz question
    Supports both direct transcript input and memory-based content
    """
    if not answer or len(answer.strip()) < 5:
        raise HTTPException(status_code=400, detail="Answer must be at least 5 characters")

    try:
        # Get transcript from memory if use_memory is true
        if use_memory.lower() == 'true':
            # Use session_id from form or cookie
            effective_session_id = session_id or cookie_session_id

            if not effective_session_id or effective_session_id not in lecture_memory:
                raise HTTPException(status_code=400, detail="No memory found. Please add sources first.")

            transcript = lecture_memory[effective_session_id]["combined_text"]
            if not transcript or len(transcript.strip()) < 50:
                raise HTTPException(status_code=400, detail="Memory is empty. Please add sources first.")

        if not transcript or len(transcript.strip()) < 50:
            raise HTTPException(status_code=400, detail="Transcript is required")

        evaluation = evaluate_answer(question, answer, transcript, knowledge_level)
        
        return JSONResponse({
            "success": True,
            "evaluation": evaluation
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ask_question")
async def ask_question(
    transcript: str = Form(...),
    question: str = Form(...),
    knowledge_level: int = Form(...),
    language: str = Form(default='en')
):
    """
    Answer a question about the transcript based on user's knowledge level in specified language
    """
    if not question or len(question.strip()) < 5:
        raise HTTPException(status_code=400, detail="Question must be at least 5 characters")
    
    if not transcript or len(transcript.strip()) < 50:
        raise HTTPException(status_code=400, detail="Transcript required")
    
    level_descriptions = {
        0: "complete beginner with no prior knowledge",
        1: "beginner with basic familiarity",
        2: "intermediate learner with solid foundation",
        3: "advanced learner with strong background",
        4: "expert with deep technical knowledge"
    }
    
    language_names = {
        'en': 'English',
        'es': 'Spanish',
        'fr': 'French',
        'de': 'German',
        'zh': 'Chinese',
        'ja': 'Japanese',
        'ar': 'Arabic',
        'hi': 'Hindi',
        'pt': 'Portuguese',
        'ru': 'Russian'
    }
    
    language_instruction = f"Respond in {language_names.get(language, 'English')}." if language != 'en' else ""
    
    try:
        print(f"Answering question at level {knowledge_level} in {language}...")
        message = anthropic_client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=1500,
            messages=[{
                "role": "user",
                "content": f"""{language_instruction}

You are helping a {level_descriptions.get(knowledge_level, 'intermediate')} understand this lecture.

Lecture Transcript:
{transcript}

Student's Question: {question}

Provide a clear, helpful answer tailored to their knowledge level. Be conversational and educational."""
            }]
        )
        
        answer = message.content[0].text
        print("Question answered successfully!")
        
        return JSONResponse({
            "success": True,
            "answer": answer
        })
        
    except Exception as e:
        print(f"Question answering error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/upload_document")
async def upload_document(file: UploadFile = File(...)):
    """
    Upload and extract text from document files
    Supports: PDF, DOCX, PPTX, TXT
    Returns extracted text for review before summarization
    """
    try:
        print(f"Received document upload: {file.filename}")

        # Validate file
        file_bytes = await FileValidator.validate_document(file)

        # Extract text based on file type
        extracted_text, file_type = DocumentExtractor.extract_text(file_bytes, file.filename)

        print(f"Successfully extracted {len(extracted_text)} characters from {file_type}")

        # Determine simple type for frontend
        extension = file.filename.lower().split('.')[-1]
        simple_type = {
            'pdf': 'pdf',
            'doc': 'document',
            'docx': 'document',
            'ppt': 'presentation',
            'pptx': 'presentation',
            'txt': 'text'
        }.get(extension, 'document')

        return JSONResponse({
            "success": True,
            "text": extracted_text,
            "filename": file.filename,
            "character_count": len(extracted_text),
            "type": simple_type,
            "file_type": file_type
        })

    except HTTPException as e:
        print(f"Document upload error: {e.detail}")
        raise e
    except Exception as e:
        print(f"Unexpected document error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/upload_pdf")
async def upload_pdf(file: UploadFile = File(...)):
    """
    Legacy endpoint for PDF uploads (redirects to upload_document)
    Maintained for backwards compatibility
    """
    return await upload_document(file)


@app.post("/upload_audio_stream")
async def upload_audio_stream(
    file: UploadFile = File(...),
    language: str = Form(default="en")
):
    """
    Upload and transcribe audio file with streaming progress
    """
    import json

    async def generate():
        try:
            print(f"Received audio upload: {file.filename} (language: {language})")

            # Send initial status
            yield f"data: {json.dumps({'status': 'uploading', 'message': 'Processing audio file...'})}\n\n"

            # Validate file
            audio_bytes = await FileValidator.validate_audio(file)

            yield f"data: {json.dumps({'status': 'validating', 'message': 'File validated, starting transcription...'})}\n\n"

            # Map language codes
            whisper_language = language if language != 'en' else None

            yield f"data: {json.dumps({'status': 'transcribing', 'message': 'Transcribing audio...'})}\n\n"

            # Stream transcription segments
            async for segment_data in transcriber.transcribe_audio_streaming(
                audio_bytes,
                file.filename,
                language=whisper_language
            ):
                if segment_data["type"] == "segment":
                    # Send segment to frontend for word-by-word display
                    yield f"data: {json.dumps({'status': 'segment', **segment_data})}\n\n"
                elif segment_data["type"] == "complete":
                    # Transcription complete
                    yield f"data: {json.dumps({'status': 'complete', 'filename': file.filename})}\n\n"
                elif segment_data["type"] == "error":
                    raise Exception(segment_data["message"])

            print("Transcription streaming complete")

        except HTTPException as e:
            error = {"status": "error", "message": e.detail}
            yield f"data: {json.dumps(error)}\n\n"
        except Exception as e:
            error = {"status": "error", "message": str(e)}
            yield f"data: {json.dumps(error)}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")

@app.post("/upload_audio")
async def upload_audio(
    file: UploadFile = File(...),
    language: str = Form(default="en")
):
    """
    Upload and transcribe audio file (non-streaming version for compatibility)
    Returns transcribed text for review before summarization
    """
    try:
        print(f"Received audio upload: {file.filename} (language: {language})")

        # Validate file
        audio_bytes = await FileValidator.validate_audio(file)

        # Map language codes (Whisper supports: en, es, fr, de, zh, ja, ar, hi, pt, ru)
        # Frontend uses same codes as Whisper
        whisper_language = language if language != 'en' else None

        # Transcribe audio
        transcribed_text = await transcriber.transcribe_audio(
            audio_bytes,
            file.filename,
            language=whisper_language
        )

        print(f"Successfully transcribed {len(transcribed_text)} characters from audio")

        return JSONResponse({
            "success": True,
            "text": transcribed_text,
            "filename": file.filename,
            "character_count": len(transcribed_text),
            "type": "audio",
            "language": language
        })

    except HTTPException as e:
        print(f"Audio upload error: {e.detail}")
        raise e
    except Exception as e:
        print(f"Unexpected audio error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# MEMORY MANAGEMENT ENDPOINTS
# ============================================================================

@app.post("/memory/add")
async def add_to_memory(
    request: Request,
    response: Response,
    session_id: Optional[str] = Cookie(default=None)
):
    """
    Add content to session memory
    Accepts text, PDF, or audio content with source metadata
    """
    try:
        body = await request.json()
        text = body.get('text', '').strip()
        source_type = body.get('source_type', 'text')
        filename = body.get('filename', 'Unnamed')

        if not text or len(text) < 10:
            raise HTTPException(status_code=400, detail="Content must be at least 10 characters")

        # Check for session_id in request body first, then fall back to cookie
        if not session_id:
            session_id = body.get('session_id')

        # Generate session ID if not exists
        if not session_id:
            session_id = str(uuid.uuid4())
            print(f"Creating new session: {session_id}")
        else:
            print(f"Using existing session: {session_id}")

        # Always set the cookie to ensure it's refreshed
        response.set_cookie(
            key="session_id",
            value=session_id,
            max_age=86400,  # 24 hours
            httponly=False,  # Changed to allow JavaScript to read it
            samesite="lax",
            path="/"
        )

        # Initialize memory for session if not exists
        if session_id not in lecture_memory:
            lecture_memory[session_id] = {"sources": [], "combined_text": ""}
            print(f"Initialized new memory for session: {session_id}")

        # Create source entry
        source_entry = {
            "type": source_type,
            "filename": filename,
            "text": text,
            "timestamp": datetime.now().isoformat(),
            "preview": text[:200] + "..." if len(text) > 200 else text
        }

        # Add to memory
        lecture_memory[session_id]["sources"].append(source_entry)

        # Rebuild combined text with source labels
        combined_parts = []
        for idx, source in enumerate(lecture_memory[session_id]["sources"], 1):
            type_label = {
                "text": "Text Input",
                "pdf": "PDF Document",
                "audio": "Audio Transcription"
            }.get(source["type"], "Unknown Source")

            combined_parts.append(f"=== Source {idx}: {type_label} - {source['filename']} ===\n\n{source['text']}\n\n")

        lecture_memory[session_id]["combined_text"] = "\n".join(combined_parts)

        print(f"Added source to memory. Session: {session_id}, Total sources: {len(lecture_memory[session_id]['sources'])}")

        return JSONResponse({
            "success": True,
            "session_id": session_id,
            "source_count": len(lecture_memory[session_id]["sources"]),
            "combined_length": len(lecture_memory[session_id]["combined_text"]),
            "source_added": source_entry
        })

    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Memory add error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/memory/get")
async def get_memory(session_id: Optional[str] = Cookie(default=None)):
    """
    Get current session memory contents
    Returns all sources and combined text
    """
    try:
        if not session_id or session_id not in lecture_memory:
            return JSONResponse({
                "success": True,
                "sources": [],
                "combined_text": "",
                "source_count": 0
            })

        memory = lecture_memory[session_id]

        return JSONResponse({
            "success": True,
            "sources": memory["sources"],
            "combined_text": memory["combined_text"],
            "source_count": len(memory["sources"])
        })

    except Exception as e:
        print(f"Memory get error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/memory/remove/{index}")
async def remove_from_memory(
    index: int,
    session_id: Optional[str] = Cookie(default=None)
):
    """
    Remove a specific source from memory by index
    Rebuilds combined text after removal
    """
    try:
        if not session_id or session_id not in lecture_memory:
            raise HTTPException(status_code=404, detail="No session found")

        memory = lecture_memory[session_id]

        if index < 0 or index >= len(memory["sources"]):
            raise HTTPException(status_code=400, detail="Invalid source index")

        # Remove source
        removed_source = memory["sources"].pop(index)

        # Rebuild combined text
        combined_parts = []
        for idx, source in enumerate(memory["sources"], 1):
            type_label = {
                "text": "Text Input",
                "pdf": "PDF Document",
                "audio": "Audio Transcription"
            }.get(source["type"], "Unknown Source")

            combined_parts.append(f"=== Source {idx}: {type_label} - {source['filename']} ===\n\n{source['text']}\n\n")

        memory["combined_text"] = "\n".join(combined_parts)

        print(f"Removed source {index} from memory. Remaining sources: {len(memory['sources'])}")

        return JSONResponse({
            "success": True,
            "removed": removed_source,
            "source_count": len(memory["sources"]),
            "combined_length": len(memory["combined_text"])
        })

    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Memory remove error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/memory/clear")
async def clear_memory(
    response: Response,
    session_id: Optional[str] = Cookie(default=None)
):
    """
    Clear all memory for current session
    Removes session from memory and clears cookie
    """
    try:
        if session_id and session_id in lecture_memory:
            del lecture_memory[session_id]
            print(f"Cleared memory for session: {session_id}")

        # Clear cookie
        response.delete_cookie(key="session_id")

        return JSONResponse({
            "success": True,
            "message": "Memory cleared successfully"
        })

    except Exception as e:
        print(f"Memory clear error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/config")
async def get_config():
    """
    Return current configuration for frontend
    """
    return JSONResponse({
        "whisper_mode": config.WHISPER_MODE.value,
        "max_pdf_size_mb": config.MAX_PDF_SIZE / (1024 * 1024),
        "max_audio_size_mb": config.MAX_AUDIO_SIZE / (1024 * 1024),
        "supported_audio_formats": list(config.AUDIO_FORMATS),
        "whisper_model_size": config.WHISPER_MODEL_SIZE if config.WHISPER_MODE == WhisperMode.LOCAL else None
    })


@app.get("/health")
async def health_check():
    """
    Health check endpoint
    """
    return {"status": "healthy", "message": "Adaptive Lecture Summarizer is running"}

if __name__ == "__main__":
    import uvicorn
    print("Starting Adaptive Lecture Summarizer...")
    print("Open your browser to: http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
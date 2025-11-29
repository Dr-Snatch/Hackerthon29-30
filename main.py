"""
Adaptive Lecture Summarizer - Backend
Clean separation: Python backend only
"""

import os
from typing import Optional

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from fastapi.middleware.cors import CORSMiddleware
import anthropic
from dotenv import load_dotenv

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


def evaluate_answer(question: str, user_answer: str, transcript: str, knowledge_level: int) -> dict:
    """
    Evaluate a user's natural language answer to a quiz question
    Returns feedback and assessment
    """
    try:
        print(f"Evaluating answer for level {knowledge_level}...")
        message = anthropic_client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=1000,
            messages=[{
                "role": "user",
                "content": f"""Evaluate this student's answer to a quiz question based on the lecture content.

Question: {question}

Student's Answer: {user_answer}

Lecture Content (for reference):
{transcript}

Provide constructive feedback that:
1. Acknowledges what they got right
2. Gently corrects any misconceptions
3. Adds helpful context or connections they might have missed
4. Encourages further learning

Be supportive and educational, not harsh. Match the tone to someone learning at this level.

Return your response as JSON in this format:
{{
  "score": "correct|partial|incorrect",
  "feedback": "Your detailed feedback here"
}}

Return ONLY the JSON, no other text."""
            }]
        )
        
        response_text = message.content[0].text.strip()
        print("Answer evaluated successfully!")
        print(f"Raw response: {response_text[:200]}...")
        
        # Remove markdown code blocks if present
        if response_text.startswith('```'):
            # Remove ```json and ``` markers
            response_text = response_text.replace('```json', '').replace('```', '').strip()
        
        # Parse JSON response
        import json
        evaluation = json.loads(response_text)
        
        return evaluation
        
    except Exception as e:
        print(f"Answer evaluation error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Answer evaluation failed: {str(e)}")


async def generate_single_level_stream(transcript: str, level: int, level_name: str):
    """
    Generate a single summary level with streaming using Haiku (fast!)
    """
    level_descriptions = {
        0: ("COMPLETE BEGINNER (0.0-0.2)", "Assumes absolutely no prior knowledge. Define every technical term in simple language. Use everyday analogies. Build from first principles. Be patient and thorough."),
        1: ("BEGINNER (0.2-0.4)", "Assumes basic familiarity with the topic area. Still explain technical terms but can assume some foundational concepts. Use clear examples."),
        2: ("INTERMEDIATE (0.4-0.6)", "Assumes solid foundational knowledge. Use standard technical terminology. Focus on connections between concepts and practical applications."),
        3: ("ADVANCED (0.6-0.8)", "Assumes strong technical background. Use advanced terminology freely. Focus on nuances, implications, and deeper understanding."),
        4: ("EXPERT (0.8-1.0)", "Assumes expert-level knowledge. Be concise and dense. Focus on cutting-edge insights, edge cases, research implications, and what's novel or significant.")
    }
    
    level_label, level_desc = level_descriptions[level]
    
    try:
        with anthropic_client.messages.stream(
            model="claude-haiku-4-20250514",  # Using Haiku for speed!
            max_tokens=1500,
            messages=[{
                "role": "user",
                "content": f"""Create a summary of this lecture transcript for a **{level_label}** student.

{level_desc}

Transcript:
{transcript}

Provide:
## Key Concepts
## Core Takeaways  
## Important Details
## Suggested Focus Areas"""
            }]
        ) as stream:
            buffer = ""
            for text in stream.text_stream:
                buffer += text
                yield {
                    'level': level,
                    'text': text,
                    'buffer': buffer
                }
    except Exception as e:
        print(f"Error generating level {level}: {str(e)}")
        yield {
            'level': level,
            'error': str(e)
        }


async def generate_all_summaries_stream(transcript: str):
    """
    Generate all 5 levels in PARALLEL using Haiku
    Much faster than sequential!
    """
    try:
        print("Starting PARALLEL streaming summary generation with Haiku...")
        
        # Send initial test message
        yield f"data: {json_module.dumps({'type': 'test', 'message': 'Stream started'})}\n\n"
        
        # Storage for each level's content
        level_buffers = {0: "", 1: "", 2: "", 3: "", 4: ""}
        
        # Create 5 parallel tasks
        tasks = [
            generate_single_level_stream(transcript, level, f"Level {level}")
            for level in range(5)
        ]
        
        # Process streams as they arrive
        import asyncio
        async def process_level(level_gen, level_num):
            async for chunk in level_gen:
                if 'error' in chunk:
                    yield {'level': level_num, 'error': chunk['error']}
                else:
                    yield chunk
        
        # Merge all streams
        from itertools import cycle
        active_tasks = [process_level(task, i) for i, task in enumerate(tasks)]
        
        # Simple approach: iterate through tasks in round-robin
        while active_tasks:
            for i, task in enumerate(list(active_tasks)):
                try:
                    chunk = await task.__anext__()
                    
                    level = chunk['level']
                    if 'error' in chunk:
                        print(f"Level {level} error: {chunk['error']}")
                        continue
                    
                    # Send content chunk
                    yield f"data: {json_module.dumps({'type': 'content', 'text': chunk['text'], 'level': level})}\n\n"
                    
                    level_buffers[level] = chunk['buffer']
                    
                except StopAsyncIteration:
                    active_tasks.remove(task)
                    print(f"Level {i} complete")
                except Exception as e:
                    print(f"Error in level {i}: {str(e)}")
                    active_tasks.remove(task)
        
        # Send final summaries
        yield f"data: {json_module.dumps({'type': 'summaries', 'data': level_buffers})}\n\n"
        
        # Send completion event
        yield f"data: {json_module.dumps({'type': 'complete'})}\n\n"
        print("Parallel streaming complete!")
        
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


def evaluate_answer(question: str, user_answer: str, transcript: str, knowledge_level: int) -> dict:
    """
    Evaluate a user's natural language answer to a quiz question
    Returns feedback and assessment
    """
    try:
        print(f"Evaluating answer for level {knowledge_level}...")
        message = anthropic_client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=1000,
            messages=[{
                "role": "user",
                "content": f"""Evaluate this student's answer to a quiz question based on the lecture content.

Question: {question}

Student's Answer: {user_answer}

Lecture Content (for reference):
{transcript}

Provide constructive feedback that:
1. Acknowledges what they got right
2. Gently corrects any misconceptions
3. Adds helpful context or connections they might have missed
4. Encourages further learning

Be supportive and educational, not harsh. Match the tone to someone learning at this level.

Return your response as JSON in this format:
{{
  "score": "correct|partial|incorrect",
  "feedback": "Your detailed feedback here"
}}

Return ONLY the JSON, no other text."""
            }]
        )
        
        response_text = message.content[0].text.strip()
        print("Answer evaluated successfully!")
        
        # Parse JSON response
        import json
        evaluation = json.loads(response_text)
        
        return evaluation
        
    except Exception as e:
        print(f"Answer evaluation error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Answer evaluation failed: {str(e)}")
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

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """
    Serve the main HTML interface
    """
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/process_stream")
async def process_lecture_stream(request: Request):
    """
    Process lecture transcript and stream all 5 adaptive summaries
    """
    try:
        body = await request.json()
        transcript = body.get('transcript', '')
        
        # Validate transcript
        if not transcript or len(transcript.strip()) < 50:
            raise HTTPException(status_code=400, detail="Transcript must be at least 50 characters")
        
        return StreamingResponse(
            generate_all_summaries_stream(transcript),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            }
        )
    except Exception as e:
        print(f"Streaming error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

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


@app.post("/evaluate_answer")
async def check_answer(
    question: str = Form(...),
    answer: str = Form(...),
    transcript: str = Form(...),
    knowledge_level: int = Form(...)
):
    """
    Evaluate a user's answer to a quiz question
    """
    if not answer or len(answer.strip()) < 5:
        raise HTTPException(status_code=400, detail="Answer must be at least 5 characters")
    
    try:
        evaluation = evaluate_answer(question, answer, transcript, knowledge_level)
        
        return JSONResponse({
            "success": True,
            "evaluation": evaluation
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
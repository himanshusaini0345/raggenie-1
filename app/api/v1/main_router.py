from app.providers.cache_manager import cache_manager
from fastapi import APIRouter, Depends, File, HTTPException, status, Query, BackgroundTasks, UploadFile
from fastapi.encoders import jsonable_encoder
from app.models.request import Chat, FeedbackCorrectionRequest
from starlette.requests import Request
from loguru import logger
from app.schemas import llmchat as schemas
from app.api.v1 import llmchat
from app.api.v1 import connector
from sqlalchemy.orm import Session
from app.utils.database import get_db
import time
import uuid
from fastapi.responses import FileResponse, StreamingResponse
from fastapi import APIRouter, Depends, File, HTTPException, status, Query, BackgroundTasks, UploadFile, Form
from fastapi.encoders import jsonable_encoder
from app.models.request import Chat, FeedbackCorrectionRequest
from starlette.requests import Request
from loguru import logger
from app.schemas import llmchat as schemas
from app.api.v1 import llmchat
from app.api.v1 import connector
from sqlalchemy.orm import Session
from app.utils.database import get_db
import time
import uuid
import os
import tempfile
import io
from groq import Groq
from typing import Optional
import aiofiles


MainRouter = APIRouter()

async def save_data(chat_id, context_id, content, out, chat_context, user_id,config_id, env_id, db, datasources):
    resp = await llmchat.create_chat(
        schemas.ChatHistoryCreate(
            chat_id = chat_id,
            chat_context_id=context_id,
            chat_query=content,
            chat_answer= jsonable_encoder(out),
            chat_context = jsonable_encoder({}),
            chat_summary=out.get("summary", content),
            user_id=user_id,
            configuration_id=config_id,
            environment_id=env_id
        ),
        db
    )
    logger.info(f"saving chat to database")
    if resp.status:
        chat_id = resp.data["chat"].chat_id
    if len(out.get("data",[])) == 0 and out.get("intent","") == "database_agent":
        success, err = datasources.get("database_agent").insert_chat_history(
        chat_id=chat_id,
        chat_context_id=context_id,
        chat_query=content,
        chat_answer=out if len(out) > 0 else {},
        chat_context={},
        chat_summary=out.get("summary", content),
        user_id=user_id,
        primary_chat=True
        )

        if not success:
            logger.error(f"Failed to save chat: {err}")


@MainRouter.post("/query", status_code=status.HTTP_201_CREATED)
async def qna(
    query: Chat,
    request: Request,
    background_tasks: BackgroundTasks,
    context_id: str = Query(..., alias="contextId"),
    config_id: str = Query(..., alias="configId"),
    env_id: str = Query(..., alias="envId"),
    user_id: int = Query(..., alias="userId"),
    db: Session = Depends(get_db),
):

    """
    Handles user queries and invokes the chain to get an answer from the LLM.

    Args:
        query (Chat): User query as a Chat model.
        request (Request): FastAPI request object containing context and app-level dependencies.
        background_tasks (BackgroundTasks): Background task for asynchronous logging.
        db (Session): Database session dependency.

    Returns:
        dict: Response containing the answer to the user's query and the original query text.
    """
    
    logger.info(f"{context_id} - {config_id} - query: {query.content}")
    cached_data = cache_manager.get(int(config_id))
    if not cached_data:
        logger.info("configuration was not found in the cache")
        response = await connector.create_yaml(request, int(config_id), db, False)
        if response['success'] == True:
            cached_data = cache_manager.get(int(config_id))
        else:
            return
        
    chain = cached_data["chain"]
    vector_store = cached_data['vector_store']
    request.app.chain = chain
    request.app.vector_store = vector_store
    user_role = query.role

    if user_role == "user" or user_role == "it test":
        user_role = "developer"

    start_time = time.time()

    out = await chain.invoke({
        "question": query.content,
        "context_id": context_id,
        "user_role" : user_role
    })

    chat_context = out.get("chat_context", {})
    out.pop("chat_context", None)
    chat_id = str(uuid.uuid4())
    datasources = request.app.container.datasources()
    # background_tasks.add_task(
    #     save_data, chat_id, context_id, query.content, out.copy(), chat_context, user_id, config_id, env_id, db, datasources
    # )
    resp = await llmchat.create_chat(
        schemas.ChatHistoryCreate(
            chat_id = chat_id,
            chat_context_id=context_id,
            chat_query=query.content,
            chat_answer= jsonable_encoder(out),
            chat_context = jsonable_encoder({}),
            chat_summary=out.get("summary", query.content),
            user_id=user_id,
            configuration_id=config_id,
            environment_id=env_id
        ),
        db
    )
    logger.info(f"saving chat to database")
    if resp.status:
        chat_id = resp.data["chat"].chat_id
    if len(out.get("data",[])) == 0 and out.get("intent","") == "database_agent":
        success, err = datasources.get("database_agent").insert_chat_history(
        chat_id=chat_id,
        chat_context_id=context_id,
        chat_query=query.content,
        chat_answer=out if len(out) > 0 else {},
        chat_context={},
        chat_summary=out.get("summary", query.content),
        user_id=user_id,
        primary_chat=True
        )

        if not success:
            logger.error(f"Failed to save chat: {err}")

    logger.info(f"out:{out}")

    end_time = time.time()
    total_response_time = end_time - start_time
    logger.debug(f"total_response_time:{total_response_time}")
    return {
        "response": out,
        "query": query.content,
        "chat_id": chat_id,
    }


#! This api is not in use right now, instead we are using a scheduler for the feedback_correction job
@MainRouter.post("/feedback_correction", status_code=status.HTTP_201_CREATED)
def feedback_correction(request: Request, body: FeedbackCorrectionRequest):

    """
    Processes feedback from LLM responses and updates the vector store accordingly.

    Args:
        request (Request): FastAPI request object containing the app's vector store.
        body (FeedbackCorrectionRequest): Request body containing user feedback to be processed.

    Returns:
        str: Success message indicating the feedback processing outcome.

    """

    store = request.app.vector_store

    if body.responses:
        for response in body.responses:
            similar_sample = store.find_similar_samples(response.description)
            if len(similar_sample) > 0 and similar_sample[0]['distances'] < 0.3:
                store.update_store(similar_sample[0]['id'],response.metadata,response.description)
            else:
                store.update_store(metadatas = response.metadata,documents = response.description)
        return "Success: Feedback received and processed."

    else:
        return "Success: No Feedback received and processed."


# Initialize Groq client (make sure to set GROQ_API_KEY in your environment)
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

from io import BytesIO

async def transcribe_audio(audio_file: UploadFile) -> str:
    try:
        content = await audio_file.read()
        file_obj = BytesIO(content)
        file_obj.name = audio_file.filename  # whisper expects a filename

        transcription = groq_client.audio.transcriptions.create(
            file=file_obj,
            model="whisper-large-v3",
            language="en"
        )

        return transcription.text

    except Exception as e:
        logger.error(f"Error transcribing audio: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error transcribing audio: {str(e)}"
        )

async def generate_speech(text: str) -> bytes:
    """
    Generate speech from text using Groq's PlayAI TTS model
    """
    try:
        # Generate speech using Groq
        speech_response = groq_client.audio.speech.create(
            model="playai-tts",
            voice="Cheyenne-PlayAI",  # You can make this configurable
            input=text,
            response_format="mp3"
        )
        
        return speech_response.content
    
    except Exception as e:
        logger.error(f"Error generating speech: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating speech: {str(e)}"
        )

@MainRouter.post("/voice-query", status_code=status.HTTP_201_CREATED)
async def voice_qna(
    request: Request,
    background_tasks: BackgroundTasks,
    audio_file: UploadFile = File(..., description="Audio file for voice input"),
    context_id: str = Form(...),
    config_id: str = Form(...),
    env_id: str = Form(...),
    user_id: int = Form(...),
    role: str = Form(default="user", description="User role"),
    voice_output: bool = Form(default=True, description="Whether to return voice output"),
    voice_model: str = Form(default="alloy", description="Voice model for TTS (alloy, echo, fable, onyx, nova, shimmer)"),
    db: Session = Depends(get_db),
):  
    # Validate audio file
    if not audio_file.content_type.startswith('audio/'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must be an audio file"
        )
    
    try:
        logger.info(f"{context_id} - {config_id} - processing voice query from user {user_id}")
        
        # Step 1: Transcribe audio to text using Groq Whisper
        logger.info("Transcribing audio...")
        transcribed_text = await transcribe_audio(audio_file)
        logger.info(f"Transcribed text: {transcribed_text}")
        
        # Step 2: Get cached configuration
        cached_data = cache_manager.get(int(config_id))
        if not cached_data:
            logger.info("configuration was not found in the cache")
            response = await connector.create_yaml(request, int(config_id), db, False)
            if response['success'] == True:
                cached_data = cache_manager.get(int(config_id))
            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Configuration not found and could not be created"
                )
        
        # Step 3: Process the query using existing chain logic
        chain = cached_data["chain"]
        vector_store = cached_data['vector_store']
        request.app.chain = chain
        request.app.vector_store = vector_store
        logger.info(f"role{role}")
        
        user_role = role if role != "user" or role != "it test" else "developer"
        
        start_time = time.time()
        out = await chain.invoke({
            "question": transcribed_text,
            "context_id": context_id,
            "user_role": user_role
        })
        
        chat_context = out.get("chat_context", {})
        out.pop("chat_context", None)
        chat_id = str(uuid.uuid4())
        
        # Step 4: Save to database in background
        background_tasks.add_task(
            save_data, chat_id, context_id, transcribed_text, out, 
            chat_context, user_id, config_id, env_id, db
        )
        
        end_time = time.time()
        total_response_time = end_time - start_time
        logger.info(f"Query processed in {total_response_time:.2f} seconds")
        
        # Step 5: Prepare response
        response_text = out.get("summary", "")  # Adjust based on your response structure
        logger.info(f"response_text:{response_text}")
        
        if not voice_output:
            # Return text response
            return {
                "transcription": transcribed_text,
                "response": out,
                "query": transcribed_text,
                "chat_id": chat_id,
                "processing_time": total_response_time
            }
        
        # Step 6: Generate speech output using Groq TTS
        logger.info("Generating speech output...")
        
        # Update the TTS call to use the voice_model parameter
        speech_response = groq_client.audio.speech.create(
            model="playai-tts",
            voice="Cheyenne-PlayAI",
            input=response_text,
            response_format="mp3"
        )
        
        audio_content = speech_response.read()
        
        # Return audio response as streaming response
        return StreamingResponse(
            io.BytesIO(audio_content),
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": f"attachment; filename=response_{chat_id}.mp3",
                "X-Chat-ID": chat_id,
                "X-Transcription": transcribed_text,
                "X-Processing-Time": str(total_response_time)
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing voice query: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing voice query: {str(e)}"
        )

@MainRouter.post("/text-to-speech", status_code=status.HTTP_200_OK)
async def text_to_speech(
    text: str = Form(..., description="Text to convert to speech"),
    voice_model: str = Form(default="alloy", description="Voice model for TTS (alloy, echo, fable, onyx, nova, shimmer)"),
):
    """
    Convert text to speech using Groq's PlayAI TTS model.
    
    Args:
        text (str): Text to convert to speech.
        voice_model (str): Voice model for TTS.
    
    Returns:
        StreamingResponse: Audio file stream.
    """
    
    try:
        logger.info(f"Converting text to speech: {text[:50]}...")
        
        # Generate speech using Groq
        speech_response = groq_client.audio.speech.create(
            model="playai-tts",
            voice="Cheyenne-PlayAI",
            input=text,
            response_format="mp3"
        )
        
        audio_content = speech_response.content
        
        # Return audio response as streaming response
        return StreamingResponse(
            io.BytesIO(audio_content),
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": f"attachment; filename=tts_{uuid.uuid4().hex[:8]}.mp3"
            }
        )
        
    except Exception as e:
        logger.error(f"Error generating speech: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating speech: {str(e)}"
        )

@MainRouter.post("/speech-to-text", status_code=status.HTTP_200_OK)
async def speech_to_text(
    audio_file: UploadFile = File(..., description="Audio file for transcription"),
    language: Optional[str] = Form(default="en", description="Language code for transcription"),
):
    """
    Convert speech to text using Groq's Whisper-large-v3 model.
    
    Args:
        audio_file (UploadFile): Audio file to transcribe.
        language (str): Language code for transcription (optional).
    
    Returns:
        dict: Transcription result.
    """
    
    # Validate audio file
    if not audio_file.content_type.startswith('audio/'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must be an audio file"
        )
    
    try:
        logger.info(f"Transcribing audio file: {audio_file.filename}")
        
        # Transcribe audio
        transcribed_text = await transcribe_audio(audio_file)
        
        return {
            "transcription": transcribed_text,
            "language": language,
            "filename": audio_file.filename
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error transcribing audio: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error transcribing audio: {str(e)}"
        )
from phi.agent import Agent
from phi.model.openai import OpenAIChat
from app.core import settings
import asyncio
import openai
from phi.tools.firecrawl import FirecrawlTools
from textwrap import dedent

from app.utils.trafilatura_tool import TrafilaturaTools


class AgentManager:
    def __init__(self):
        self.agent = None

    async def get_image_to_text_agent(self):
        if self.agent is None:
            self.agent = Agent(
                system_prompt="""
                                You are a vision and reasoning expert. When analyzing an image:
                                
                                1. Describe all visible elements — people, objects, handwriting, background, layout, etc.
                                2. Extract any visible text, whether typed or handwritten.
                                3. If the image contains diagrams, equations, or logical steps, summarize and explain the reasoning.
                                4. If no meaningful content is found, clearly say so — do not guess.
                                
                                Always answer clearly using plain language. Be accurate, structured, and helpful.
                                """,
                markdown=True,
            )

            self.agent.model = OpenAIChat(
                id=settings.OPENAI_MODEL,
                model=settings.OPENAI_MODEL,
                max_completion_tokens=2000,
                temperature=0.3,
                api_key=settings.OPENAI_API_KEY,
                top_p=1.0
            )
        return self.agent

    async def get_audio_to_text_summary_agent(self):
        if self.agent is None:
            # Agent responsible for generating summaries from transcripts
            self.agent = Agent(
                system_prompt="""
                You are an expert conversation summarization assistant.

                You will receive a transcript generated from recorded conversations such as:
                - Customer support calls
                - Business or team meetings
                - Podcasts or interviews
                - Standard Operating Procedure (SOP) narrations
                
                Your tasks:
                1. Accurately identify the topic and purpose of the conversation.
                2. Extract and summarize key ideas, decisions made, action items, or valuable insights.
                3. Ignore filler words, small talk, and any irrelevant noise or chit-chat.
                4. If the transcript lacks meaningful content, clearly state: "No meaningful content found."
                
                Format your output as a **clear and structured summary**, using bullets or short paragraphs as appropriate.
                Always be concise, accurate, and context-aware.
                """,
                markdown=True,
            )

            self.agent.model = OpenAIChat(
                id=settings.OPENAI_MODEL,
                model=settings.OPENAI_MODEL,
                max_completion_tokens=2000,
                temperature=0.2,
                api_key=settings.OPENAI_API_KEY,
                top_p=1.0
            )

        return self.agent

    @staticmethod
    async def transcribe_audio(audio_file_path):
        client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)

        with open(audio_file_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                file=audio_file,
                model="whisper-1"
            )

        return transcript.text

    async def summarize_audio(self, audio_file_path):
        agent = await self.get_audio_to_text_summary_agent()

        # # Step 1: Transcribe audio using Whisper
        transcript = await self.transcribe_audio(audio_file_path)

        summary_prompt = f"""
        Summarize the following audio transcript:
        \"\"\"
        {transcript}
        \"\"\"
        """

        # Step 2: Generate summary using the agent
        response = await asyncio.to_thread(agent.run,
                                           message=summary_prompt
                                           )
        return response.content

    async def get_vector_query_agent(self):
        if self.agent is None:
            self.agent = Agent(
                system_prompt="""
                                You are an expert at transforming user prompts into precise, targeted vector search queries. 
                                Your primary task is to identify and distill the core intent or main subject from natural language inputs.

                                Instructions:
                                - Clearly pinpoint the central topic or intent of each prompt.
                                - Omit all greetings, pleasantries, and unnecessary context.
                                - Ensure queries remain concise, specific, and directly searchable within a vector database.
                                - Do not add explanations, examples, or extraneous information—only output the refined query.
                                
                                You will get user prompt as input and you need to transform it into a vector search query to search vector chunks from database.
                                
                                Example: Function Analysis Report for XYZ Solutions Private Limited, India and XYZ Solutions LLC, UAE
                                """,
                markdown=True,
            )

            self.agent.model = OpenAIChat(
                id=settings.OPENAI_MODEL,
                model=settings.OPENAI_MODEL,
                max_completion_tokens=50,
                temperature=0.1,
                api_key=settings.OPENAI_API_KEY,
                top_p=1.0
            )
        return self.agent

    async def get_webpage_summary_agent(self):
        if self.agent is None:
            self.agent = Agent(
                name="web researcher and content extractor",
                system_prompt=dedent("""
                                You are an expert web researcher and content extractor.
                                Extract comprehensive, structured information from the provided webpage. Focus on:

                                1. Accurately capturing the page title, description, and key features
                                2. Identifying and extracting main content sections with their headings
                                3. Finding important links to related pages or resources
                                4. Locating contact information if available
                                5. Extracting relevant metadata that provides context about the site
                                """),
                markdown=True,
                tools=[TrafilaturaTools()]
            )

            self.agent.model = OpenAIChat(
                id=settings.OPENAI_MODEL,
                model=settings.OPENAI_MODEL,
                max_completion_tokens=2000,
                temperature=0.3,
                api_key=settings.OPENAI_API_KEY,
                top_p=1.0
            )
        return self.agent
